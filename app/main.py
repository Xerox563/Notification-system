from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.api import admin, bulk, health, notifications, templates, users
from app.config import get_settings
from app.core.idempotency import IdempotencyStore
from app.core.queue import RedisQueue
from app.db import create_tables, make_engine, make_session_factory
from app.logging_config import setup_logging
from app.services.errors import ConflictError, InvalidRequest, NotFoundError, ServiceError

STATUS_FOR_ERROR = {NotFoundError: 404, InvalidRequest: 422, ConflictError: 409}


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    engine = make_engine()
    await create_tables(engine)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)

    app.state.settings = settings
    app.state.session_factory = make_session_factory(engine)
    app.state.queue = RedisQueue(redis, settings.visibility_timeout_seconds)
    app.state.idempotency = IdempotencyStore(redis, settings.idempotency_ttl_seconds)
    yield
    await redis.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Notification System", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError):
        return JSONResponse({"detail": exc.message}, status_code=STATUS_FOR_ERROR.get(type(exc), 400))

    for module in (users, templates, bulk, notifications, admin, health):
        app.include_router(module.router)
    return app


app = create_app()
