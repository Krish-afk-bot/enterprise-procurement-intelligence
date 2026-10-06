"""Security baseline tests — startup guards and JWT secret policy.

These tests verify that:
  1. Production startup refuses a known-weak JWT secret.
  2. Development startup accepts the same weak secret but does not error.
  3. Production startup accepts a suitably strong secret.
  4. The is_jwt_secret_safe() helper returns the correct verdict.
"""

from __future__ import annotations

import pytest

from app.config.settings import _KNOWN_WEAK_SECRETS, Settings

# ------------------------------------------------------------------ helpers


def prod_settings(**overrides: object) -> Settings:
    """A Settings instance with app_env='production'."""
    return Settings(
        app_env="production",
        jwt_algorithm="HS256",
        database_url="sqlite+aiosqlite:///./var/test.db",
        **overrides,  # type: ignore[arg-type]
    )


def dev_settings(**overrides: object) -> Settings:
    return Settings(
        app_env="development",
        jwt_algorithm="HS256",
        database_url="sqlite+aiosqlite:///./var/test.db",
        **overrides,  # type: ignore[arg-type]
    )


# ------------------------------------------------------------------ production guard


class TestProductionStartupSecurity:
    def test_known_weak_secret_raises_in_production(self) -> None:
        """validate_startup_security must raise for any known-weak default."""
        for weak in list(_KNOWN_WEAK_SECRETS)[:3]:
            s = prod_settings(jwt_secret=weak)
            with pytest.raises(RuntimeError, match="refused"):
                s.validate_startup_security()

    def test_short_secret_raises_in_production(self) -> None:
        """A secret shorter than 32 characters must be rejected in production."""
        s = prod_settings(jwt_secret="short-but-not-default-123")
        with pytest.raises(RuntimeError, match="32 characters"):
            s.validate_startup_security()

    def test_strong_secret_accepted_in_production(self) -> None:
        strong = "a" * 48  # 48 chars, not in known-weak list
        s = prod_settings(jwt_secret=strong)
        # Must not raise
        s.validate_startup_security()

    def test_32_char_secret_accepted_in_production(self) -> None:
        exactly_32 = "x" * 32
        s = prod_settings(jwt_secret=exactly_32)
        s.validate_startup_security()

    def test_31_char_secret_rejected_in_production(self) -> None:
        s = prod_settings(jwt_secret="y" * 31)
        with pytest.raises(RuntimeError):
            s.validate_startup_security()


# ------------------------------------------------------------------ development tolerance


class TestDevelopmentStartupSecurity:
    def test_weak_secret_does_not_raise_in_development(self) -> None:
        """Development mode must never raise on validate_startup_security."""
        s = dev_settings(jwt_secret="dev-insecure-change-me")
        # Must not raise — development is allowed to use the default
        s.validate_startup_security()

    def test_is_jwt_secret_safe_returns_false_for_weak_in_production(self) -> None:
        s = prod_settings(jwt_secret="dev-insecure-change-me")
        assert s.is_jwt_secret_safe() is False

    def test_is_jwt_secret_safe_returns_true_for_strong_in_production(self) -> None:
        s = prod_settings(jwt_secret="a" * 48)
        assert s.is_jwt_secret_safe() is True

    def test_is_jwt_secret_safe_returns_true_in_development_always(self) -> None:
        # Development always reports safe so startup logging is not blocked
        s = dev_settings(jwt_secret="dev-insecure-change-me")
        assert s.is_jwt_secret_safe() is True
