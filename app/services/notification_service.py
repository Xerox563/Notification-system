from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import Priority, Status
from app.core.idempotency import IdempotencyStore
from app.core.queue import RedisQueue
from app.metrics import NOTIFICATIONS_CREATED
from app.models import Notification, Template, User
from app.models.base import new_id
from app.schemas.notification import NotificationCreate
from app.services.errors import ConflictError, InvalidRequest, NotFoundError
from app.services.preference_service import get_preference
from app.services.quiet_hours import quiet_hours_end
from app.services.template_service import render


def as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def recipient_for(user: User, channel: str) -> str:
    address = {"email": user.email, "sms": user.phone, "push": user.device_token}[channel]
    if not address:
        raise InvalidRequest(f"user has no address for {channel}")
    return address


async def find_template(session: AsyncSession, name: str) -> Template:
    result = await session.execute(select(Template).where(Template.name == name))
    template = result.scalar_one_or_none()
    if template is None:
        raise NotFoundError("template not found")
    return template


async def find_by_key(session: AsyncSession, key: str) -> Notification | None:
    result = await session.execute(select(Notification).where(Notification.idempotency_key == key))
    return result.scalar_one_or_none()


async def create_notification(
    session: AsyncSession,
    queue: RedisQueue,
    idem: IdempotencyStore,
    data: NotificationCreate,
    idempotency_key: str | None = None,
    bulk_id: str | None = None,
) -> tuple[Notification, bool]:
    user = await session.get(User, data.user_id)
    if user is None:
        raise NotFoundError("user not found")

    template = await find_template(session, data.template)
    if template.channel != data.channel.value:
        raise InvalidRequest("template belongs to a different channel")

    recipient = recipient_for(user, data.channel.value)
    context = {"name": user.name, **data.payload}
    missing = [v for v in template.variables if v not in context]
    if missing:
        raise InvalidRequest(f"missing payload values: {', '.join(missing)}")
    subject, body = render(template.subject, template.body, context)

    notification_id = new_id()
    if idempotency_key:
        existing_id = await idem.reserve(idempotency_key, notification_id)
        if existing_id:
            existing = await session.get(Notification, existing_id)
            if existing is None:
                raise ConflictError("a request with this key is still being processed")
            return existing, True

    priority = data.priority.value
    status = Status.queued
    last_error = None
    run_at = as_utc(data.send_at) if data.send_at else None

    pref = await get_preference(session, user.id, data.channel.value)
    if pref is not None and not pref.enabled:
        status = Status.skipped
        last_error = "user opted out of this channel"
    else:
        if pref is not None and data.priority != Priority.high:
            when = run_at or datetime.now(timezone.utc)
            quiet_end = quiet_hours_end(when, user.timezone, pref.quiet_start, pref.quiet_end)
            if quiet_end is not None:
                run_at = quiet_end
        if run_at is not None and run_at > datetime.now(timezone.utc):
            status = Status.scheduled

    notification = Notification(
        id=notification_id,
        user_id=user.id,
        channel=data.channel.value,
        template_id=template.id,
        payload=data.payload,
        recipient=recipient,
        subject=subject,
        body=body,
        priority=priority,
        status=status.value,
        last_error=last_error,
        send_at=run_at,
        idempotency_key=idempotency_key,
        bulk_id=bulk_id,
    )
    session.add(notification)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        if idempotency_key:
            existing = await find_by_key(session, idempotency_key)
            if existing is not None:
                return existing, True
        raise

    if status != Status.skipped:
        job = {"id": notification.id, "attempt": 0}
        await queue.enqueue(data.channel.value, priority, job, run_at.timestamp() if run_at else None)
    NOTIFICATIONS_CREATED.labels(data.channel.value, priority, status.value).inc()
    return notification, False
