from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.queue import RedisQueue
from app.models import BulkJob, User
from app.schemas.notification import BulkCreate
from app.services.errors import InvalidRequest, NotFoundError
from app.services.notification_service import find_template

BULK_CHANNEL = "bulk"


async def resolve_audience(session: AsyncSession, data: BulkCreate, limit: int) -> list[str]:
    if data.user_ids:
        user_ids = list(dict.fromkeys(data.user_ids))
    else:
        result = await session.execute(select(User.id).limit(limit + 1))
        user_ids = list(result.scalars())
    if len(user_ids) > limit:
        raise InvalidRequest(f"bulk requests are limited to {limit} users")
    return user_ids


async def start_bulk(session: AsyncSession, queue: RedisQueue, data: BulkCreate, settings: Settings) -> BulkJob:
    template = await find_template(session, data.template)
    if template.channel != data.channel.value:
        raise InvalidRequest("template belongs to a different channel")

    user_ids = await resolve_audience(session, data, settings.bulk_max_users)
    job = BulkJob(total=len(user_ids), status="processing" if user_ids else "completed")
    session.add(job)
    await session.commit()

    size = settings.bulk_chunk_size
    for start in range(0, len(user_ids), size):
        chunk = {
            "bulk_id": job.id,
            "user_ids": user_ids[start : start + size],
            "channel": data.channel.value,
            "template": data.template,
            "payload": data.payload,
            "priority": data.priority.value,
            "attempt": 0,
        }
        await queue.enqueue(BULK_CHANNEL, "normal", chunk)
    return job


async def record_progress(session: AsyncSession, bulk_id: str, processed: int, failed: int) -> None:
    await session.execute(
        update(BulkJob)
        .where(BulkJob.id == bulk_id)
        .values(processed=BulkJob.processed + processed, failed=BulkJob.failed + failed)
    )
    await session.execute(
        update(BulkJob)
        .where(BulkJob.id == bulk_id, BulkJob.processed + BulkJob.failed >= BulkJob.total)
        .values(status="completed")
    )
    await session.commit()


async def get_bulk(session: AsyncSession, bulk_id: str) -> BulkJob:
    job = await session.get(BulkJob, bulk_id)
    if job is None:
        raise NotFoundError("bulk job not found")
    return job
