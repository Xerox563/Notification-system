from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import new_id, utcnow


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    channel: Mapped[str] = mapped_column(String(16))
    template_id: Mapped[str] = mapped_column(ForeignKey("templates.id"))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    recipient: Mapped[str] = mapped_column(String(255), default="")
    subject: Mapped[str] = mapped_column(String(255), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(8), default="normal")
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    send_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    bulk_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    notification_id: Mapped[str] = mapped_column(ForeignKey("notifications.id"), index=True)
    attempt_no: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
