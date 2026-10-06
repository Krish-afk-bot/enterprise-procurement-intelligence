"""Cache / rate-limit / queue substrate.

Cache keys are always namespaced with tenant and (where relevant) user identity
so a cached answer can never leak across authorization contexts (PRD s.57).
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from app.observability.logging import get_logger
from app.providers.types import ProviderStatus

logger = get_logger(__name__)


def scoped_key(*parts: Any) -> str:
    """Build an authorization-scoped cache key."""
    return ":".join("" if part is None else str(part) for part in parts)


class MemoryCache:
    name = "memory"

    def __init__(self) -> None:
        self._store: dict[str, tuple[float | None, Any]] = {}
        self._lock = asyncio.Lock()

    def _expired(self, entry: tuple[float | None, Any]) -> bool:
        expires_at, _ = entry
        return expires_at is not None and expires_at < time.time()

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if self._expired(entry):
            self._store.pop(key, None)
            return None
        return entry[1]

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        expires = time.time() + ttl_seconds if ttl_seconds else None
        self._store[key] = (expires, value)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def incr(self, key: str, ttl_seconds: int | None = None) -> int:
        async with self._lock:
            current = await self.get(key)
            value = int(current or 0) + 1
            expires = time.time() + ttl_seconds if ttl_seconds else None
            existing = self._store.get(key)
            if existing and existing[0] is not None and not self._expired(existing):
                expires = existing[0]
            self._store[key] = (expires, value)
            return value

    async def ttl(self, key: str) -> int | None:
        entry = self._store.get(key)
        if entry is None or entry[0] is None:
            return None
        return max(0, int(entry[0] - time.time()))

    async def clear_prefix(self, prefix: str) -> int:
        keys = [k for k in self._store if k.startswith(prefix)]
        for key in keys:
            self._store.pop(key, None)
        return len(keys)

    async def status(self) -> ProviderStatus:
        now = time.time()
        live = sum(1 for expires, _ in self._store.values() if expires is None or expires > now)
        return ProviderStatus.of("cache", self.name, True, detail="in-process TTL cache", entries=live)


class RedisCache:
    name = "redis"

    def __init__(self, url: str) -> None:
        self.url = url
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import redis.asyncio as redis_async

            self._client = redis_async.from_url(self.url, decode_responses=True)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get(self, key: str) -> Any | None:
        raw = await self._get_client().get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return raw

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        payload = json.dumps(value, default=str)
        if ttl_seconds:
            await self._get_client().setex(key, ttl_seconds, payload)
        else:
            await self._get_client().set(key, payload)

    async def delete(self, key: str) -> None:
        await self._get_client().delete(key)

    async def incr(self, key: str, ttl_seconds: int | None = None) -> int:
        client = self._get_client()
        value = int(await client.incr(key))
        if ttl_seconds and value == 1:
            await client.expire(key, ttl_seconds)
        return value

    async def ttl(self, key: str) -> int | None:
        ttl = await self._get_client().ttl(key)
        return None if ttl in (-1, -2) else int(ttl)

    async def clear_prefix(self, prefix: str) -> int:
        client = self._get_client()
        removed = 0
        async for key in client.scan_iter(match=f"{prefix}*", count=500):
            await client.delete(key)
            removed += 1
        return removed

    async def status(self) -> ProviderStatus:
        try:
            await self._get_client().ping()
            return ProviderStatus.of("cache", self.name, True, detail=f"connected to {self.url}")
        except Exception as exc:  # noqa: BLE001
            return ProviderStatus.of("cache", self.name, False, detail=f"unreachable: {type(exc).__name__}")


CacheLike = MemoryCache | RedisCache


class RateLimiter:
    """Fixed-window counter on top of any cache provider."""

    def __init__(self, cache: CacheLike, *, enabled: bool = True, window_seconds: int = 60) -> None:
        self.cache = cache
        self.enabled = enabled
        self.window_seconds = window_seconds

    async def check(self, bucket: str, scope: str, limit: int) -> tuple[bool, int, int]:
        """Return ``(allowed, remaining, retry_after_seconds)``."""
        if not self.enabled or limit <= 0:
            return True, limit, 0
        window = int(time.time() // self.window_seconds)
        key = f"rl:{bucket}:{scope}:{window}"
        count = await self.cache.incr(key, ttl_seconds=self.window_seconds)
        remaining = max(0, limit - count)
        retry_after = 0 if count <= limit else self.window_seconds - int(time.time() % self.window_seconds)
        return count <= limit, remaining, retry_after
