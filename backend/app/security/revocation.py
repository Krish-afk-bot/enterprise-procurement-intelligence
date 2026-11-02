"""Refresh-token rotation: a jti denylist backed by the cache provider.

Every refresh token carries a unique ``jti``. When a token is rotated the
presented ``jti`` is revoked for the remainder of that token's lifetime, so a
stolen copy can only be used until its legitimate owner refreshes. Presenting an
already-revoked token is treated as reuse and rejected.

The store is backed by ``CacheLike`` (in-memory locally, Redis in production) so
revocations are shared across workers when Redis is configured.
"""

from __future__ import annotations

from app.providers.cache import CacheLike

_PREFIX = "auth:revoked_refresh:"


class RefreshTokenStore:
    def __init__(self, cache: CacheLike | None) -> None:
        # A missing cache means "no revocation tracking" (e.g. a unit test that
        # builds the router without a started container). Rotation still issues
        # fresh tokens; only reuse detection is disabled.
        self.cache = cache

    @staticmethod
    def _key(jti: str) -> str:
        return f"{_PREFIX}{jti}"

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        if not jti or self.cache is None:
            return
        await self.cache.set(self._key(jti), True, ttl_seconds=max(1, ttl_seconds))

    async def is_revoked(self, jti: str) -> bool:
        if not jti or self.cache is None:
            return False
        return await self.cache.get(self._key(jti)) is not None
