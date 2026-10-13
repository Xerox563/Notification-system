from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.constants import Channel, Priority


class NotificationCreate(BaseModel):
    user_id: str
    channel: Channel
    template: str
    payload: dict = Field(default_factory=dict)
    priority: Priority = Priority.normal
    send_at: datetime | None = None


class AttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attempt_no: int
    provider: str
    status: str
    error: str | None
    created_at: datetime


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    channel: str
    priority: str
    status: str
    attempts: int
    last_error: str | None
    send_at: datetime | None
    bulk_id: str | None
    created_at: datetime
    updated_at: datetime


class NotificationDetail(NotificationOut):
    subject: str
    body: str
    delivery_attempts: list[AttemptOut] = Field(default_factory=list)


class BulkCreate(BaseModel):
    user_ids: list[str] | None = None
    segment: str | None = None
    channel: Channel
    template: str
    payload: dict = Field(default_factory=dict)
    priority: Priority = Priority.low

    @model_validator(mode="after")
    def need_audience(self):
        if bool(self.user_ids) == bool(self.segment):
            raise ValueError("send either user_ids or segment")
        if self.segment is not None and self.segment != "all":
            raise ValueError("only the all segment is supported")
        return self


class BulkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    total: int
    processed: int
    failed: int
    status: str
    created_at: datetime
