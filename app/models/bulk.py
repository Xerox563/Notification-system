from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import new_id, utcnow


class BulkJob(Base):
    __tablename__ = "bulk_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    total: Mapped[int] = mapped_column(Integer, default=0)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="processing")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
