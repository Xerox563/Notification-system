import time

from redis.asyncio import Redis

TOKEN_BUCKET = """
local capacity = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])

local data = redis.call('HMGET', KEYS[1], 'tokens', 'ts')
local tokens = tonumber(data[1])
local ts = tonumber(data[2])
if tokens == nil then
    tokens = capacity
    ts = now
end

tokens = math.min(capacity, tokens + (now - ts) * rate)
local allowed = 0
if tokens >= cost then
    tokens = tokens - cost
    allowed = 1
end

redis.call('HSET', KEYS[1], 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', KEYS[1], math.ceil(capacity / rate) + 60)
return allowed
"""


class RateLimiter:
    def __init__(self, redis: Redis, clock=time.time):
        self.redis = redis
        self.clock = clock
        self.script = redis.register_script(TOKEN_BUCKET)

    async def allow(self, key: str, capacity: int, per_second: float, cost: int = 1) -> bool:
        result = await self.script(keys=[f"rl:{key}"], args=[capacity, per_second, self.clock(), cost])
        return result == 1

    async def allow_user(self, user_id: str, channel: str, capacity: int, per_second: float) -> bool:
        return await self.allow(f"user:{user_id}:{channel}", capacity, per_second)

    async def allow_provider(self, provider: str, capacity: int, per_second: float) -> bool:
        return await self.allow(f"provider:{provider}", capacity, per_second)
