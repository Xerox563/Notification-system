import asyncio
import logging
import random

from app.config import Settings
from app.constants import FINAL_STATUSES, Status
from app.core.circuit_breaker import CircuitBreaker
from app.core.queue import RedisQueue, Reserved
from app.core.rate_limiter import RateLimiter
from app.core.retry import backoff_delay, should_retry
from app.metrics import BREAKER_STATE, DEAD_LETTERED, DELIVERIES, RETRIES
from app.models import DeliveryAttempt, Notification
from app.providers.base import Message, Provider

log = logging.getLogger("worker")


class DeliveryWorker:
    def __init__(
        self,
        channel: str,
        providers: list[Provider],
        queue: RedisQueue,
        limiter: RateLimiter,
        session_factory,
        settings: Settings,
    ):
        self.channel = channel
        self.providers = providers
        self.queue = queue
        self.limiter = limiter
        self.session_factory = session_factory
        self.settings = settings
        self.breakers = {
            p.name: CircuitBreaker(settings.breaker_failure_threshold, settings.breaker_recovery_seconds)
            for p in providers
        }

    async def run(self, stop: asyncio.Event) -> None:
        consumers = [asyncio.create_task(self.consume(stop)) for _ in range(self.settings.worker_concurrency)]
        await asyncio.gather(*consumers)

    async def consume(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            reserved = await self.queue.dequeue(self.channel)
            if reserved is None:
                try:
                    await asyncio.wait_for(stop.wait(), self.settings.poll_interval_seconds)
                except asyncio.TimeoutError:
                    pass
                continue
            try:
                await self.handle(reserved)
            except Exception:
                log.exception("job failed unexpectedly, it will return after the visibility timeout")

    async def handle(self, reserved: Reserved) -> None:
        job = reserved.job
        attempt = job["attempt"]

        async with self.session_factory() as session:
            notification = await session.get(Notification, job["id"])
            if notification is None or notification.status in FINAL_STATUSES:
                await self.queue.ack(reserved)
                return

            s = self.settings
            if not await self.limiter.allow_user(
                notification.user_id, self.channel, s.user_rate_capacity, s.user_rate_per_second
            ):
                await self.queue.retry(reserved, job, random.uniform(1, 3))
                return

            outcome = await self.try_providers(session, notification, attempt)

            if outcome["sent"]:
                notification.status = Status.delivered.value if outcome["delivered"] else Status.sent.value
                notification.attempts = attempt + 1
                notification.last_error = None
                await session.commit()
                await self.queue.ack(reserved)
                return

            if outcome["throttled"] and not outcome["errors"]:
                await session.commit()
                await self.queue.retry(reserved, job, random.uniform(1, 3))
                return

            error = "; ".join(outcome["errors"]) or "no provider available"
            notification.attempts = attempt + 1
            notification.last_error = error

            if should_retry(attempt, s.max_attempts):
                await session.commit()
                delay = backoff_delay(attempt, s.backoff_base_seconds, s.backoff_cap_seconds)
                await self.queue.retry(reserved, {**job, "attempt": attempt + 1}, delay)
                RETRIES.labels(self.channel).inc()
            else:
                notification.status = Status.failed.value
                await session.commit()
                await self.queue.dead_letter(reserved, job)
                DEAD_LETTERED.labels(self.channel).inc()

    async def try_providers(self, session, notification: Notification, attempt: int) -> dict:
        outcome = {"sent": False, "delivered": False, "throttled": False, "errors": []}
        message = Message(notification.id, notification.recipient, notification.subject, notification.body)
        s = self.settings

        for provider in self.providers:
            breaker = self.breakers[provider.name]
            if not await self.limiter.allow_provider(
                provider.name, s.provider_rate_capacity, s.provider_rate_per_second
            ):
                outcome["throttled"] = True
                continue
            if not breaker.allow():
                outcome["errors"].append(f"{provider.name} circuit open")
                continue

            try:
                result = await provider.send(message)
            except Exception as exc:
                breaker.record_failure()
                BREAKER_STATE.labels(provider.name).set(breaker.state_value)
                DELIVERIES.labels(self.channel, provider.name, "failed").inc()
                session.add(self.attempt_row(notification, attempt, provider, "failed", str(exc)))
                outcome["errors"].append(str(exc))
                continue

            breaker.record_success()
            BREAKER_STATE.labels(provider.name).set(breaker.state_value)
            DELIVERIES.labels(self.channel, provider.name, "sent").inc()
            session.add(self.attempt_row(notification, attempt, provider, "sent", None))
            outcome["sent"] = True
            outcome["delivered"] = result.delivered
            return outcome

        return outcome

    @staticmethod
    def attempt_row(notification, attempt, provider, status, error) -> DeliveryAttempt:
        return DeliveryAttempt(
            notification_id=notification.id,
            attempt_no=attempt + 1,
            provider=provider.name,
            status=status,
            error=error,
        )
