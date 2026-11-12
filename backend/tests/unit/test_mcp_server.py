"""Tests for the MCP tool boundary.

These cover the properties the server promises, without needing a model or a
network: the deployment-bound identity, permission enforcement, the timeout, the
rate limit, output validation, and that every registered tool declares a
permission the policy layer actually knows.
"""

from __future__ import annotations

import asyncio

import pytest

from app.config.settings import Settings
from app.mcp_server import POLICIES, McpConfigError, ToolGuard, ToolOutputError, ToolRateLimited, ToolTimeout
from app.mcp_server.guards import ToolPolicy, bind_principal, validate_policies
from app.mcp_server.server import build_server
from app.security.rbac import ALL_PERMISSIONS, Principal

TENANT = "ten_test"


def principal(role: str = "admin") -> Principal:
    return Principal(user_id="usr_1", tenant_id=TENANT, email="tools@epi.local", role=role)


def settings(**overrides: object) -> Settings:
    base = {
        "mcp_enabled": True,
        "mcp_tenant_id": TENANT,
        "mcp_user_email": "tools@epi.local",
        "mcp_role": "admin",
    }
    return Settings(**{**base, **overrides})


class Recorder:
    def __init__(self) -> None:
        self.records: list[dict] = []

    async def __call__(self, record: dict) -> None:
        self.records.append(record)


class TestIdentity:
    def test_missing_tenant_is_refused(self) -> None:
        with pytest.raises(McpConfigError, match="MCP_TENANT_ID"):
            bind_principal(settings(mcp_tenant_id=None))

    def test_missing_account_is_refused(self) -> None:
        with pytest.raises(McpConfigError, match="MCP_USER_EMAIL"):
            bind_principal(settings(mcp_user_email=None))

    def test_unknown_role_is_refused(self) -> None:
        with pytest.raises(McpConfigError, match="MCP_ROLE"):
            bind_principal(settings(mcp_role="superuser"))

    def test_disabled_server_is_refused(self) -> None:
        with pytest.raises(McpConfigError, match="disabled"):
            bind_principal(settings(mcp_enabled=False))

    def test_binding_uses_the_deployment_tenant(self) -> None:
        bound = bind_principal(settings(mcp_role="viewer"))
        assert bound.tenant_id == TENANT
        assert bound.role == "viewer"
        assert bound.email == "tools@epi.local"


class TestPolicies:
    def test_every_tool_permission_is_known(self) -> None:
        validate_policies(POLICIES)
        assert {policy.permission for policy in POLICIES.values()} <= ALL_PERMISSIONS

    def test_unknown_permission_is_rejected(self) -> None:
        with pytest.raises(McpConfigError, match="unknown permissions"):
            validate_policies(
                {"bad": ToolPolicy(name="bad", permission="root:everything", description="")}
            )

    async def test_registered_tools_match_the_policies(self) -> None:
        server = build_server(settings(), principal=principal())
        tools = await server.list_tools()
        names = {tool.name for tool in tools}
        assert names == set(POLICIES)


class TestGuard:
    async def test_permission_is_enforced_and_audited(self) -> None:
        recorder = Recorder()
        guard = ToolGuard(principal=principal("viewer"), audit_writer=recorder)
        policy = ToolPolicy(name="admin_only", permission="admin:write", description="")

        with pytest.raises(Exception):
            await guard.call(policy, _ok)

        assert recorder.records and recorder.records[0]["outcome"] == "denied"

    async def test_allowed_call_is_audited(self) -> None:
        recorder = Recorder()
        guard = ToolGuard(principal=principal("admin"), audit_writer=recorder)
        policy = ToolPolicy(name="documents_read", permission="documents:read", description="")

        result = await guard.call(policy, _ok)

        assert result == {"ok": True}
        assert recorder.records[-1]["outcome"] == "success"

    async def test_timeout_is_enforced(self) -> None:
        guard = ToolGuard(principal=principal(), timeout_seconds=0.05)
        policy = ToolPolicy(name="slow", permission="documents:read", description="")

        with pytest.raises(ToolTimeout):
            await guard.call(policy, _slow)

    async def test_rate_limit_is_enforced(self) -> None:
        guard = ToolGuard(principal=principal(), rate_limit_per_minute=2)
        policy = ToolPolicy(name="limited", permission="documents:read", description="")

        await guard.call(policy, _ok)
        await guard.call(policy, _ok)
        with pytest.raises(ToolRateLimited):
            await guard.call(policy, _ok)

    async def test_non_json_output_is_rejected(self) -> None:
        guard = ToolGuard(principal=principal())
        policy = ToolPolicy(name="opaque", permission="documents:read", description="")

        with pytest.raises(ToolOutputError):
            await guard.call(policy, _opaque)


async def _ok(**_: object) -> dict:
    return {"ok": True}


async def _slow(**_: object) -> dict:
    await asyncio.sleep(0.5)
    return {"ok": True}


async def _opaque(**_: object) -> object:
    return object()
