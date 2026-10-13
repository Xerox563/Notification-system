from fastapi import APIRouter, Depends
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_queue, get_session
from app.constants import Channel, Status
from app.core.queue import RedisQueue
from app.models import Notification

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/queues")
async def queue_depths(queue: RedisQueue = Depends(get_queue)):
    channels = [c.value for c in Channel] + ["bulk"]
    return {channel: await queue.depths(channel) for channel in channels}


@router.post("/dlq/replay")
async def replay_dead_letters(
    channel: Channel,
    limit: int = 1000,
    session: AsyncSession = Depends(get_session),
    queue: RedisQueue = Depends(get_queue),
):
    replayed = await queue.replay_dlq(channel.value, limit)
    if replayed:
        await session.execute(
            update(Notification)
            .where(Notification.id.in_(replayed))
            .values(status=Status.queued.value, attempts=0, last_error=None)
        )
        await session.commit()
    return {"channel": channel.value, "replayed": len(replayed)}
