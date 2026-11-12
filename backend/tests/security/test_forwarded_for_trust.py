"""Client identity must not be spoofable through X-Forwarded-For.

Unauthenticated rate limits (login, upload) are scoped by client address. If the
header is trusted unconditionally, a caller can rotate it and receive a fresh
bucket per request, which defeats the limit entirely.
"""

from __future__ import annotations

from starlette.requests import Request

from app.api.deps import get_client_ip
from app.config.settings import Settings


def make_request(headers: dict[str, str] | None = None, client: str = "203.0.113.7") -> Request:
    raw_headers = [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": raw_headers,
            "client": (client, 12345),
        }
    )


def settings(**overrides) -> Settings:
    return Settings(app_env="test", jwt_secret="test-secret-not-for-production", **overrides)


def test_forwarded_header_is_ignored_by_default() -> None:
    request = make_request({"x-forwarded-for": "198.51.100.9"})
    assert get_client_ip(request, settings()) == "203.0.113.7"


def test_forwarded_header_is_used_only_when_trusted() -> None:
    request = make_request({"x-forwarded-for": "198.51.100.9, 10.0.0.1"})
    assert get_client_ip(request, settings(trust_forwarded_for=True)) == "198.51.100.9"


def test_missing_client_falls_back_to_none() -> None:
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    assert get_client_ip(request, settings()) is None
