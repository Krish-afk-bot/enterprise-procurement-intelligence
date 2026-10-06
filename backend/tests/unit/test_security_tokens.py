"""Unit tests for app.security.tokens — JWT and password hashing.

Pure unit tests: no I/O, no database, no HTTP.
"""

from __future__ import annotations

import time

import pytest

from app.core.errors import AuthenticationError
from app.security.tokens import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_token,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)


# ------------------------------------------------------------------ fixtures

@pytest.fixture()
def settings(settings):  # noqa: F811 — shadows session-scoped conftest fixture
    return settings


# ------------------------------------------------------------------ password hashing

class TestHashPassword:
    def test_hash_is_not_plaintext(self) -> None:
        hashed = hash_password("secret123")
        assert hashed != "secret123"
        assert len(hashed) > 20

    def test_same_password_different_hashes(self) -> None:
        """Argon2 uses a random salt, so two calls must not match."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2

    def test_verify_correct_password(self) -> None:
        hashed = hash_password("correct-horse")
        assert verify_password("correct-horse", hashed) is True

    def test_verify_wrong_password(self) -> None:
        hashed = hash_password("correct-horse")
        assert verify_password("wrong-password", hashed) is False

    def test_verify_empty_password_fails(self) -> None:
        hashed = hash_password("nonempty")
        assert verify_password("", hashed) is False

    def test_needs_rehash_on_fresh_hash(self) -> None:
        hashed = hash_password("test")
        # A freshly generated hash should not need rehashing.
        assert needs_rehash(hashed) is False

    def test_needs_rehash_on_garbage(self) -> None:
        assert needs_rehash("not-a-valid-hash") is True


# ------------------------------------------------------------------ JWT

class TestCreateDecodeToken:
    def test_roundtrip_access_token(self, settings) -> None:
        token, expires_at = create_token(
            settings,
            subject="usr_abc",
            tenant_id="ten_xyz",
            role="viewer",
        )
        payload = decode_token(settings, token)
        assert payload["sub"] == "usr_abc"
        assert payload["tid"] == "ten_xyz"
        assert payload["role"] == "viewer"
        assert payload["typ"] == ACCESS_TOKEN_TYPE

    def test_roundtrip_refresh_token(self, settings) -> None:
        token, _ = create_token(
            settings,
            subject="usr_abc",
            tenant_id="ten_xyz",
            role="admin",
            token_type=REFRESH_TOKEN_TYPE,
        )
        payload = decode_token(settings, token, expected_type=REFRESH_TOKEN_TYPE)
        assert payload["typ"] == REFRESH_TOKEN_TYPE

    def test_wrong_token_type_raises(self, settings) -> None:
        token, _ = create_token(
            settings,
            subject="usr_abc",
            tenant_id="ten_xyz",
            role="viewer",
            token_type=ACCESS_TOKEN_TYPE,
        )
        with pytest.raises(AuthenticationError, match="refresh"):
            decode_token(settings, token, expected_type=REFRESH_TOKEN_TYPE)

    def test_tampered_token_raises(self, settings) -> None:
        token, _ = create_token(
            settings, subject="usr", tenant_id="ten", role="viewer"
        )
        tampered = token[:-4] + "XXXX"
        with pytest.raises(AuthenticationError):
            decode_token(settings, tampered)

    def test_wrong_secret_raises(self, settings) -> None:
        from app.config.settings import Settings

        token, _ = create_token(
            settings, subject="usr", tenant_id="ten", role="viewer"
        )
        bad_settings = settings.model_copy(update={"jwt_secret": "wrong-secret"})
        with pytest.raises(AuthenticationError):
            decode_token(bad_settings, token)

    def test_issuer_claim_is_epi(self, settings) -> None:
        token, _ = create_token(
            settings, subject="usr", tenant_id="ten", role="viewer"
        )
        import jwt as pyjwt
        payload = pyjwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
        assert payload["iss"] == "epi"

    def test_extra_claims_included(self, settings) -> None:
        token, _ = create_token(
            settings,
            subject="usr",
            tenant_id="ten",
            role="viewer",
            extra={"custom_claim": "value"},
        )
        payload = decode_token(settings, token)
        assert payload["custom_claim"] == "value"
