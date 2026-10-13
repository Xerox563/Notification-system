from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_idempotency, get_queue, get_session
from app.constants import Status
from app.core.idempotency import IdempotencyStore
from app.core.queue import RedisQueue
from app.models import DeliveryAttempt, Notification
from app.schemas.notification import NotificationCreate, NotificationDetail, NotificationOut
from app.services.notification_service import create_notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("", response_model=NotificationOut, status_code=202)
async def send_notification(
    data: NotificationCreate,
    response: Response,
    idempotency_key: str | None = Header(default=None, max_length=128),
    session: AsyncSession = Depends(get_session),
    queue: RedisQueue = Depends(get_queue),
    idem: IdempotencyStore = Depends(get_idempotency),
):
    notification, replay = await create_notification(session, queue, idem, data, idempotency_key)
    if replay:
        response.headers["Idempotent-Replay"] = "true"
    return notification


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    user_id: str, limit: int = 50, session: AsyncSession = Depends(get_session)
):
    query = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(min(limit, 200))
    )
    return list((await session.execute(query)).scalars())


@router.get("/{notification_id}", response_model=NotificationDetail)
async def get_notification(notification_id: str, session: AsyncSession = Depends(get_session)):
    notification = await session.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(404, "notification not found")
    attempts = await session.execute(
        select(DeliveryAttempt)
        .where(DeliveryAttempt.notification_id == notification_id)
        .order_by(DeliveryAttempt.created_at)
    )
    detail = NotificationDetail.model_validate(notification)
    detail.delivery_attempts = list(attempts.scalars())
    return detail


@router.post("/{notification_id}/delivered", response_model=NotificationOut)
async def mark_delivered(notification_id: str, session: AsyncSession = Depends(get_session)):
    notification = await session.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(404, "notification not found")
    if notification.status != Status.sent.value:
        raise HTTPException(409, "only sent notifications can be marked delivered")
    notification.status = Status.delivered.value
    await session.commit()
    return notification
