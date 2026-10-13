import asyncio
import logging

from redis.asyncio import Redis

from app.config import Settings, get_settings
from app.core.idempotency import IdempotencyStore
from app.core.process import install_signal_handlers
from app.core.queue import RedisQueue, Reserved
from app.core.retry import backoff_delay, should_retry
from app.db import create_tables, make_engine, make_session_factory
from app.logging_config import setup_logging
from app.schemas.notification import NotificationCreate
from app.services.bulk_service import BULK_CHANNEL, record_progress
from app.services.errors import ServiceError
from app.services.notification_service import create_notification

log = logging.getLogger("bulk")


class BulkWorker:
    def __init__(self, queue: RedisQueue, idem: IdempotencyStore, session_factory, settings: Settings):
        self.queue = queue
        self.idem = idem
        self.session_factory = session_factory
        self.settings = settings

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            reserved = await self.queue.dequeue(BULK_CHANNEL)
            if reserved is None:
                try:
                    await asyncio.wait_for(stop.wait(), self.settings.poll_interval_seconds)
                except asyncio.TimeoutError:
                    pass
                continue
            try:
                await self.handle(reserved)
            except Exception:
                log.exception("bulk chunk failed")
                await self.fail_chunk(reserved)

    async def handle(self, reserved: Reserved) -> None:
        chunk = reserved.job
        ok = failed = 0
        async with self.session_factory() as session:
            for user_id in chunk["user_ids"]:
                request = NotificationCreate(
                    user_id=user_id,
                    channel=chunk["channel"],
                    template=chunk["template"],
                    payload=chunk["payload"],
                    priority=chunk["priority"],
                )
                key = f"bulk:{chunk['bulk_id']}:{user_id}"
                try:
                    await create_notification(session, self.queue, self.idem, request, key, chunk["bulk_id"])
                    ok += 1
                except ServiceError:
                    failed += 1
            await record_progress(session, chunk["bulk_id"], ok, failed)
        await self.queue.ack(reserved)

    async def fail_chunk(self, reserved: Reserved) -> None:
        chunk = reserved.job
        attempt = chunk["attempt"]
        if should_retry(attempt, self.settings.max_attempts):
            s = self.settings
            delay = backoff_delay(attempt, s.backoff_base_seconds, s.backoff_cap_seconds)
            await self.queue.retry(reserved, {**chunk, "attempt": attempt + 1}, delay)
        else:
            await self.queue.dead_letter(reserved, chunk)


async def main() -> None:
    setup_logging()
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    engine = make_engine()
    await create_tables(engine)
    worker = BulkWorker(
        RedisQueue(redis, settings.visibility_timeout_seconds),
        IdempotencyStore(redis, settings.idempotency_ttl_seconds),
        make_session_factory(engine),
        settings,
    )
    stop = asyncio.Event()
    install_signal_handlers(stop)
    log.info("bulk worker started")
    await worker.run(stop)
    await redis.aclose()
    await engine.dispose()
    log.info("bulk worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
