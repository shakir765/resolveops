from typing import Any

import redis

from resolveops_core.config import settings


class RedisClient:
    def __init__(self, url: str | None = None):
        self._client = redis.Redis.from_url(url or settings.redis_url, decode_responses=True)

    @property
    def client(self) -> redis.Redis:
        return self._client

    def cache_get(self, key: str) -> str | None:
        return self._client.get(key)

    def cache_set(self, key: str, value: str, ttl: int = 300) -> None:
        self._client.setex(key, ttl, value)

    def acquire_lock(self, key: str, ttl: int | None = None) -> bool:
        return bool(self._client.set(key, "1", nx=True, ex=ttl or settings.lock_ttl_seconds))

    def release_lock(self, key: str) -> None:
        self._client.delete(key)

    def session_set(self, session_id: str, data: dict[str, Any], ttl: int = 3600) -> None:
        import json

        self._client.setex(f"session:{session_id}", ttl, json.dumps(data))

    def session_get(self, session_id: str) -> dict[str, Any] | None:
        import json

        raw = self._client.get(f"session:{session_id}")
        return json.loads(raw) if raw else None


redis_client = RedisClient()
