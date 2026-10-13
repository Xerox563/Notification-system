import asyncio
import logging

from prometheus_client import start_http_server
from redis.asyncio import Redis

from app.config import get_settings
from app.core.process import install_signal_handlers
from app.core.queue import RedisQueue
from app.core.rate_limiter import RateLimiter
from app.db import create_tables, make_engine, make_session_factory
from app.logging_config import setup_logging
from app.providers.registry import build_providers
from app.workers.worker import DeliveryWorker

log = logging.getLogger("runner")


async def run_delivery_worker(channel: str) -> None:
    setup_logging()
    settings = get_settings()
    if settings.metrics_port:
        start_http_server(settings.metrics_port)

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    engine = make_engine()
    await create_tables(engine)

    worker = DeliveryWorker(
        channel=channel,
        providers=build_providers(settings)[channel],
        queue=RedisQueue(redis, settings.visibility_timeout_seconds),
        limiter=RateLimiter(redis),
        session_factory=make_session_factory(engine),
        settings=settings,
    )

    stop = asyncio.Event()
    install_signal_handlers(stop)
    log.info("%s worker started with %s consumers", channel, settings.worker_concurrency)
    await worker.run(stop)
    await redis.aclose()
    await engine.dispose()
    log.info("%s worker stopped", channel)


def main(channel: str) -> None:
    asyncio.run(run_delivery_worker(channel))
