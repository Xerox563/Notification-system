from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_queue, get_session
from app.core.queue import RedisQueue
from app.metrics import QUEUE_DEPTH

router = APIRouter(tags=["ops"])

CHANNELS = ["email", "sms", "push", "bulk"]
PRIORITIES = ["high", "normal", "low"]


@router.get("/health")
async def health(
    response: Response, session: AsyncSession = Depends(get_session), queue: RedisQueue = Depends(get_queue)
):
    checks = {}
    try:
        await session.execute(text("select 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "down"
    try:
        await queue.redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "down"
    healthy = all(v == "ok" for v in checks.values())
    if not healthy:
        response.status_code = 503
    return {"status": "ok" if healthy else "degraded", **checks}


@router.get("/metrics")
async def metrics(queue: RedisQueue = Depends(get_queue)):
    for channel in CHANNELS:
        depths = await queue.depths(channel)
        for priority in PRIORITIES:
            QUEUE_DEPTH.labels(channel, priority).set(depths[priority])
        QUEUE_DEPTH.labels(channel, "dlq").set(depths["dlq"])
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
