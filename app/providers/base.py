from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderError(Exception):
    pass


@dataclass
class Message:
    notification_id: str
    recipient: str
    subject: str
    body: str


@dataclass
class SendResult:
    delivered: bool = False


class Provider(ABC):
    name: str
    channel: str

    @abstractmethod
    async def send(self, message: Message) -> SendResult:
        ...
