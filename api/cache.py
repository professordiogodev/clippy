"""Optional read-through cache. Redis when REDIS_URL is set, otherwise no cache at all."""

from __future__ import annotations

from typing import Protocol


class Cache(Protocol):
    kind: str

    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str) -> None: ...

    def ping(self) -> bool: ...


class NoCache:
    kind = "none"

    def get(self, key: str) -> str | None:
        return None

    def set(self, key: str, value: str) -> None:
        return None

    def ping(self) -> bool:
        return True


class RedisCache:
    kind = "redis"

    def __init__(self, url: str, ttl_seconds: int = 300) -> None:
        import redis

        self._client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
        self._ttl = ttl_seconds

    def get(self, key: str) -> str | None:
        try:
            return self._client.get(f"clippy:{key}")
        except Exception:  # a broken cache must never break redirects
            return None

    def set(self, key: str, value: str) -> None:
        try:
            self._client.set(f"clippy:{key}", value, ex=self._ttl)
        except Exception:
            return None

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except Exception:
            return False


def build_cache(redis_url: str | None, ttl_seconds: int = 300) -> Cache:
    return RedisCache(redis_url, ttl_seconds) if redis_url else NoCache()
