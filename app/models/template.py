from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import new_id


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    channel: Mapped[str] = mapped_column(String(16))
    subject: Mapped[str] = mapped_column(String(255), default="")
    body: Mapped[str] = mapped_column(Text)
    variables: Mapped[list] = mapped_column(JSON, default=list)
