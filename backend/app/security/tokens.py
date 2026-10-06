"""Password hashing and JWT issuing/verification."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from app.config.settings import Settings
from app.core.errors import AuthenticationError

_hasher = PasswordHasher()

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHashError:
        return True


def create_token(
    settings: Settings,
    *,
    subject: str,
    tenant_id: str,
    role: str,
    token_type: str = ACCESS_TOKEN_TYPE,
    extra: dict[str, Any] | None = None,
) -> tuple[str, datetime]:
    ttl = (
        settings.access_token_ttl_minutes
        if token_type == ACCESS_TOKEN_TYPE
        else settings.refresh_token_ttl_minutes
    )
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl)
    payload: dict[str, Any] = {
        "sub": subject,
        "tid": tenant_id,
        "role": role,
        "typ": token_type,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": "epi",
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_token(settings: Settings, token: str, *, expected_type: str = ACCESS_TOKEN_TYPE) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "tid"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("The token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("The token is invalid.") from exc
    if payload.get("typ") != expected_type:
        raise AuthenticationError(f"Expected a {expected_type} token.")
    return payload
