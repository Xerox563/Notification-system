from pydantic import BaseModel, ConfigDict, Field

from app.constants import Channel


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    channel: Channel
    subject: str = ""
    body: str = Field(min_length=1)


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    channel: str
    subject: str
    body: str
    variables: list[str]
