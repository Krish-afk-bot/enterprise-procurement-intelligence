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
    """A Settings instance with app_env='production' and deployed-safe flags."""
    values: dict[str, object] = {
        "app_env": "production",
        "jwt_algorithm": "HS256",
        "database_url": "sqlite+aiosqlite:///./var/test.db",
        "allow_provider_fallback": False,
        "auto_create_schema": False,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def dev_settings(**overrides: object) -> Settings:
    return Settings(
        app_env="development",
        jwt_algorithm="HS256",
        database_url="sqlite+aiosqlite:///./var/test.db",
        **overrides,  # type: ignore[arg-type]
    )


def staging_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "staging",
        "jwt_algorithm": "HS256",
        "database_url": "sqlite+aiosqlite:///./var/test.db",
        "allow_provider_fallback": False,
        "auto_create_schema": False,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


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


# ------------------------------------------------------------------ staging guard


class TestStagingStartupSecurity:
    """Staging is a non-development environment and must be guarded too."""

    def test_known_weak_secret_raises_in_staging(self) -> None:
        for weak in list(_KNOWN_WEAK_SECRETS)[:3]:
            s = staging_settings(jwt_secret=weak)
            with pytest.raises(RuntimeError, match="refused"):
                s.validate_startup_security()

    def test_short_secret_raises_in_staging(self) -> None:
        s = staging_settings(jwt_secret="short-but-not-default-123")
        with pytest.raises(RuntimeError, match="32 characters"):
            s.validate_startup_security()

    def test_strong_secret_accepted_in_staging(self) -> None:
        s = staging_settings(jwt_secret="a" * 48)
        s.validate_startup_security()  # must not raise

    def test_is_jwt_secret_safe_false_for_weak_in_staging(self) -> None:
        s = staging_settings(jwt_secret="dev-insecure-change-me")
        assert s.is_jwt_secret_safe() is False

    def test_is_jwt_secret_safe_true_for_strong_in_staging(self) -> None:
        s = staging_settings(jwt_secret="a" * 48)
        assert s.is_jwt_secret_safe() is True

    def test_is_development_false_for_staging(self) -> None:
        assert staging_settings().is_development is False

    def test_is_development_true_for_development_and_test(self) -> None:
        assert dev_settings().is_development is True
        assert Settings(
            app_env="test", database_url="sqlite+aiosqlite:///./var/test.db"
        ).is_development is True


class TestProductionConfigurationGuards:
    """Local conveniences that must fail fast when deployed."""

    def test_provider_fallback_is_refused(self) -> None:
        s = prod_settings(jwt_secret="a" * 48, allow_provider_fallback=True)
        with pytest.raises(RuntimeError, match="ALLOW_PROVIDER_FALLBACK"):
            s.validate_startup_security()

    def test_auto_create_schema_is_refused(self) -> None:
        s = prod_settings(jwt_secret="a" * 48, auto_create_schema=True)
        with pytest.raises(RuntimeError, match="AUTO_CREATE_SCHEMA"):
            s.validate_startup_security()

    def test_debug_is_refused(self) -> None:
        s = prod_settings(jwt_secret="a" * 48, debug=True)
        with pytest.raises(RuntimeError, match="DEBUG"):
            s.validate_startup_security()

    def test_wildcard_cors_is_refused(self) -> None:
        s = prod_settings(jwt_secret="a" * 48, cors_origins=["*"])
        with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
            s.validate_startup_security()

    def test_mcp_without_scope_is_refused(self) -> None:
        s = prod_settings(jwt_secret="a" * 48, mcp_enabled=True)
        with pytest.raises(RuntimeError, match="MCP_TENANT_ID"):
            s.validate_startup_security()

    def test_mcp_with_scope_is_accepted(self) -> None:
        s = prod_settings(
            jwt_secret="a" * 48,
            mcp_enabled=True,
            mcp_tenant_id="ten_x",
            mcp_user_email="ops@example.com",
        )
        s.validate_startup_security()

    def test_multiple_problems_are_reported_together(self) -> None:
        s = prod_settings(jwt_secret="short", debug=True, cors_origins=["*"])
        with pytest.raises(RuntimeError) as excinfo:
            s.validate_startup_security()
        message = str(excinfo.value)
        assert "JWT_SECRET" in message and "CORS_ORIGINS" in message and "DEBUG" in message


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
