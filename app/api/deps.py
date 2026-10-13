from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.idempotency import IdempotencyStore
from app.core.queue import RedisQueue


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


def get_queue(request: Request) -> RedisQueue:
    return request.app.state.queue


def get_idempotency(request: Request) -> IdempotencyStore:
    return request.app.state.idempotency
