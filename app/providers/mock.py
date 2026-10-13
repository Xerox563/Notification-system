import asyncio
import random

from app.providers.base import Message, Provider, ProviderError, SendResult


class MockProvider(Provider):
    def __init__(self, name: str, channel: str, failure_rate: float = 0.0, latency: float = 0.01):
        self.name = name
        self.channel = channel
        self.failure_rate = failure_rate
        self.latency = latency

    async def send(self, message: Message) -> SendResult:
        await asyncio.sleep(self.latency)
        if random.random() < self.failure_rate:
            raise ProviderError(f"{self.name} failed to send")
        return SendResult(delivered=True)
