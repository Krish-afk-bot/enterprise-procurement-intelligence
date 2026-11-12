"""Authorization, limits and audit for MCP tool calls.

An MCP server is a tool boundary, so every guarantee the HTTP API makes has to
hold here too:

* the caller's identity and tenant are established by the deployment, never by
  tool arguments — a tool cannot be talked into another tenant;
* each tool declares the permission it needs and the call is authorised before
  any work happens;
* execution is bounded by a timeout and a per-minute rate limit;
* every call is audited, including denials and timeouts;
* results must be JSON-serialisable, so a tool cannot leak an ORM object.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.config.settings import Settings
from app.db.models.tenancy import ROLES
from app.security.rbac import ALL_PERMISSIONS, Principal


class McpConfigError(RuntimeError):
    """The server refuses to start because its identity is not configured."""


class ToolTimeout(RuntimeError):
    """A tool exceeded its execution budget."""


class ToolRateLimited(RuntimeError):
    """A tool was called more often than its budget allows."""


class ToolOutputError(RuntimeError):
    """A tool returned something that is not a JSON payload."""


@dataclass(frozen=True, slots=True)
class ToolPolicy:
    name: str
    permission: str
    description: str


@dataclass(slots=True)
class ToolGuard:
    """Wraps a tool call with the checks the deployment promises."""

    principal: Principal
    timeout_seconds: float = 20.0
    rate_limit_per_minute: int = 60
    audit_writer: Callable[[dict[str, Any]], Awaitable[None]] | None = None
    _calls: dict[str, deque[float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.rate_limit_per_minute <= 0:
            raise McpConfigError("mcp_rate_limit_per_minute must be positive")
        if self.timeout_seconds <= 0:
            raise McpConfigError("mcp_tool_timeout_seconds must be positive")

    # ------------------------------------------------------------------ limits
    def _check_rate(self, name: str) -> None:
        now = time.monotonic()
        window = self._calls.setdefault(name, deque())
        while window and now - window[0] >= 60.0:
            window.popleft()
        if len(window) >= self.rate_limit_per_minute:
            raise ToolRateLimited(
                f"{name} exceeded {self.rate_limit_per_minute} calls per minute"
            )
        window.append(now)

    async def _audit(self, record: dict[str, Any]) -> None:
        if self.audit_writer is None:
            return
        try:
            await self.audit_writer(record)
        except Exception:  # noqa: BLE001 - auditing must never break a tool call
            return

    # -------------------------------------------------------------------- call
    async def call(
        self,
        policy: ToolPolicy,
        fn: Callable[..., Awaitable[Any]],
        /,
        **kwargs: Any,
    ) -> Any:
        started = time.perf_counter()
        # Authorisation comes first and covers the tool's declared permission.
        try:
            self.principal.require(policy.permission)
        except Exception:
            await self._audit(
                {
                    "action": f"mcp:{policy.name}",
                    "outcome": "denied",
                    "detail": {"permission": policy.permission, "role": self.principal.role},
                }
            )
            raise
        try:
            self._check_rate(policy.name)
            result = await asyncio.wait_for(fn(**kwargs), timeout=self.timeout_seconds)
            # No default= coercion: an ORM object, a datetime or a handle has to be
            # converted by the tool, so the boundary cannot leak internals by
            # stringifying them.
            try:
                json.dumps(result, allow_nan=False)
            except (TypeError, ValueError) as exc:
                await self._audit(
                    {
                        "action": f"mcp:{policy.name}",
                        "outcome": "invalid_output",
                        "detail": {"error": type(exc).__name__},
                    }
                )
                raise ToolOutputError(f"{policy.name} returned a non-JSON payload") from exc
        except ToolRateLimited as exc:
            await self._audit(
                {"action": f"mcp:{policy.name}", "outcome": "rate_limited", "detail": {"reason": str(exc)}}
            )
            raise
        except (asyncio.TimeoutError, TimeoutError) as exc:
            await self._audit(
                {
                    "action": f"mcp:{policy.name}",
                    "outcome": "timeout",
                    "detail": {"timeout_seconds": self.timeout_seconds},
                }
            )
            raise ToolTimeout(f"{policy.name} exceeded {self.timeout_seconds}s") from exc
        except ToolOutputError:
            raise
        except Exception as exc:  # noqa: BLE001
            await self._audit(
                {
                    "action": f"mcp:{policy.name}",
                    "outcome": "error",
                    "detail": {"error": type(exc).__name__, "message": str(exc)[:200]},
                }
            )
            raise
        await self._audit(
            {
                "action": f"mcp:{policy.name}",
                "outcome": "success",
                "detail": {
                    "permission": policy.permission,
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                },
            }
        )
        return result


def bind_principal(settings: Settings) -> Principal:
    """The identity the MCP process runs as.

    A deployment-level identity is the point: the model can choose *which* tool
    to call and with which arguments, but not whose tenant it is reading. When
    the values are absent the server refuses to start rather than defaulting to
    an administrator.
    """
    if not settings.mcp_enabled:
        raise McpConfigError("MCP is disabled (set MCP_ENABLED=true to serve tools)")
    tenant_id = (settings.mcp_tenant_id or "").strip()
    email = (settings.mcp_user_email or "").strip()
    role = (settings.mcp_role or "").strip()
    if not tenant_id:
        raise McpConfigError("MCP_TENANT_ID is required: tools must be bound to a tenant")
    if not email:
        raise McpConfigError("MCP_USER_EMAIL is required: tool calls are attributed to an account")
    if role not in ROLES:
        raise McpConfigError(f"MCP_ROLE must be one of {', '.join(ROLES)}")
    return Principal(
        user_id=f"mcp:{email}",
        tenant_id=tenant_id,
        email=email,
        role=role,
        full_name="MCP tool runtime",
    )


def validate_policies(policies: dict[str, ToolPolicy]) -> None:
    """Every declared permission must be one the policy layer knows."""
    unknown = {policy.permission for policy in policies.values()} - ALL_PERMISSIONS
    if unknown:
        raise McpConfigError(f"unknown permissions in tool policies: {sorted(unknown)}")


__all__ = [
    "McpConfigError",
    "ToolGuard",
    "ToolOutputError",
    "ToolPolicy",
    "ToolRateLimited",
    "ToolTimeout",
    "bind_principal",
    "validate_policies",
]
