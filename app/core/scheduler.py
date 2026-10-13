import asyncio
import logging

from redis.asyncio import Redis

from app.config import get_settings
from app.constants import Channel
from app.core.process import install_signal_handlers
from app.core.queue import RedisQueue
from app.logging_config import setup_logging

log = logging.getLogger("scheduler")

CHANNELS = [c.value for c in Channel] + ["bulk"]


class Scheduler:
    def __init__(self, queue: RedisQueue, channels: list[str], interval: float = 1.0):
        self.queue = queue
        self.channels = channels
        self.interval = interval

    async def tick(self) -> tuple[int, int]:
        moved = await self.queue.move_due()
        reclaimed = 0
        for channel in self.channels:
            reclaimed += await self.queue.reclaim_expired(channel)
        return moved, reclaimed

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                moved, reclaimed = await self.tick()
                if moved or reclaimed:
                    log.info("moved %s due jobs and reclaimed %s stuck jobs", moved, reclaimed)
            except Exception:
                log.exception("scheduler tick failed")
            try:
                await asyncio.wait_for(stop.wait(), self.interval)
            except asyncio.TimeoutError:
                pass


async def main() -> None:
    setup_logging()
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    queue = RedisQueue(redis, settings.visibility_timeout_seconds)
    stop = asyncio.Event()
    install_signal_handlers(stop)
    log.info("scheduler started")
    await Scheduler(queue, CHANNELS).run(stop)
    await redis.aclose()
    log.info("scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())
