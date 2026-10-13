import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.constants import Channel

CLOCK = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class UserCreate(BaseModel):
    name: str = ""
    email: EmailStr | None = None
    phone: str | None = None
    device_token: str | None = None
    timezone: str = "UTC"

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("unknown timezone") from exc
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str | None
    phone: str | None
    device_token: str | None
    timezone: str


class PreferenceIn(BaseModel):
    enabled: bool = True
    quiet_start: str | None = None
    quiet_end: str | None = None

    @field_validator("quiet_start", "quiet_end")
    @classmethod
    def valid_clock(cls, value: str | None) -> str | None:
        if value is not None and not CLOCK.match(value):
            raise ValueError("use HH:MM in 24 hour format")
        return value


class PreferenceOut(PreferenceIn):
    channel: Channel
