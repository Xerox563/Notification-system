import json
import time
from dataclasses import dataclass

from redis.asyncio import Redis

from app.constants import PRIORITY_ORDER

PRIORITY_CYCLE = ["high"] * 5 + ["normal"] * 3 + ["low"] * 1

POP_AND_TRACK = """
local job = redis.call('LPOP', KEYS[1])
if job then
    redis.call('ZADD', KEYS[2], ARGV[1], ARGV[2] .. '|' .. job)
end
return job
"""

MOVE_DUE = """
local due = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1], 'LIMIT', 0, ARGV[2])
for _, member in ipairs(due) do
    local channel, priority, body = string.match(member, '^([^|]+)|([^|]+)|(.*)$')
    redis.call('RPUSH', 'queue:' .. channel .. ':' .. priority, body)
    redis.call('ZREM', KEYS[1], member)
end
return #due
"""

RECLAIM = """
local expired = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
for _, member in ipairs(expired) do
    local priority, body = string.match(member, '^([^|]+)|(.*)$')
    redis.call('RPUSH', 'queue:' .. ARGV[2] .. ':' .. priority, body)
    redis.call('ZREM', KEYS[1], member)
end
return #expired
"""


def encode(job: dict) -> str:
    return json.dumps(job, separators=(",", ":"), sort_keys=True)


@dataclass
class Reserved:
    channel: str
    priority: str
    body: str

    @property
    def member(self) -> str:
        return f"{self.priority}|{self.body}"

    @property
    def job(self) -> dict:
        return json.loads(self.body)


class RedisQueue:
    def __init__(self, redis: Redis, visibility_timeout: int = 60, clock=time.time):
        self.redis = redis
        self.visibility_timeout = visibility_timeout
        self.clock = clock
        self.tick = 0
        self.pop_script = redis.register_script(POP_AND_TRACK)
        self.move_script = redis.register_script(MOVE_DUE)
        self.reclaim_script = redis.register_script(RECLAIM)

    @staticmethod
    def queue_key(channel: str, priority: str) -> str:
        return f"queue:{channel}:{priority}"

    @staticmethod
    def processing_key(channel: str) -> str:
        return f"processing:{channel}"

    @staticmethod
    def dlq_key(channel: str) -> str:
        return f"dlq:{channel}"

    async def enqueue(self, channel: str, priority: str, job: dict, run_at: float | None = None) -> None:
        body = encode(job)
        if run_at is not None and run_at > self.clock():
            await self.redis.zadd("delayed", {f"{channel}|{priority}|{body}": run_at})
        else:
            await self.redis.rpush(self.queue_key(channel, priority), body)

    def priority_order(self) -> list[str]:
        # the first pick rotates by weight so low priority still gets turns
        first = PRIORITY_CYCLE[self.tick % len(PRIORITY_CYCLE)]
        self.tick += 1
        return [first] + [p for p in PRIORITY_ORDER if p != first]

    async def dequeue(self, channel: str) -> Reserved | None:
        deadline = self.clock() + self.visibility_timeout
        for priority in self.priority_order():
            body = await self.pop_script(
                keys=[self.queue_key(channel, priority), self.processing_key(channel)],
                args=[deadline, priority],
            )
            if body is not None:
                return Reserved(channel, priority, body)
        return None

    async def ack(self, reserved: Reserved) -> None:
        await self.redis.zrem(self.processing_key(reserved.channel), reserved.member)

    async def retry(self, reserved: Reserved, job: dict, delay: float) -> None:
        member = f"{reserved.channel}|{reserved.priority}|{encode(job)}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.zrem(self.processing_key(reserved.channel), reserved.member)
            pipe.zadd("delayed", {member: self.clock() + delay})
            await pipe.execute()

    async def dead_letter(self, reserved: Reserved, job: dict) -> None:
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.zrem(self.processing_key(reserved.channel), reserved.member)
            pipe.rpush(self.dlq_key(reserved.channel), f"{reserved.priority}|{encode(job)}")
            await pipe.execute()

    async def move_due(self, limit: int = 500) -> int:
        return await self.move_script(keys=["delayed"], args=[self.clock(), limit])

    async def reclaim_expired(self, channel: str) -> int:
        return await self.reclaim_script(keys=[self.processing_key(channel)], args=[self.clock(), channel])

    async def depths(self, channel: str) -> dict:
        depths = {p: await self.redis.llen(self.queue_key(channel, p)) for p in PRIORITY_ORDER}
        depths["processing"] = await self.redis.zcard(self.processing_key(channel))
        depths["dlq"] = await self.redis.llen(self.dlq_key(channel))
        return depths

    async def replay_dlq(self, channel: str, limit: int = 1000) -> list[str]:
        moved: list[str] = []
        while len(moved) < limit:
            entry = await self.redis.lpop(self.dlq_key(channel))
            if entry is None:
                break
            priority, body = entry.split("|", 1)
            job = json.loads(body)
            job["attempt"] = 0
            await self.redis.rpush(self.queue_key(channel, priority), encode(job))
            moved.append(job["id"])
        return moved
