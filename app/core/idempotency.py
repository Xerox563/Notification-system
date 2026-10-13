from redis.asyncio import Redis


class IdempotencyStore:
    def __init__(self, redis: Redis, ttl_seconds: int):
        self.redis = redis
        self.ttl = ttl_seconds

    def _key(self, key: str) -> str:
        return f"idem:{key}"

    async def reserve(self, key: str, notification_id: str) -> str | None:
        created = await self.redis.set(self._key(key), notification_id, nx=True, ex=self.ttl)
        if created:
            return None
        return await self.redis.get(self._key(key))

    async def release(self, key: str) -> None:
        await self.redis.delete(self._key(key))
