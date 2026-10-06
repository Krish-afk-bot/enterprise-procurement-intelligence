"""Audit logging.

Every privileged action and every denied action is recorded with the caller, the
resource and the request id so procurement/compliance reviews are answerable
(PRD s.44/s.63).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog
from app.observability.logging import get_logger, request_id_var
from app.security.rbac import Principal

logger = get_logger(__name__)

#: Actions recorded by default (the API also records ad-hoc actions).
ACTION_LOGIN = "auth.login"
ACTION_LOGIN_FAILED = "auth.login_failed"
ACTION_LOGOUT = "auth.logout"
ACTION_REGISTER = "auth.register"
ACTION_QUERY = "query.run"
ACTION_DOCUMENT_UPLOAD = "document.upload"
ACTION_DOCUMENT_READ = "document.read"
ACTION_DOCUMENT_DELETE = "document.delete"
ACTION_DOCUMENT_REINDEX = "document.reindex"
ACTION_DOCUMENT_UPDATE = "document.update"
ACTION_COMPARE = "compare.run"
ACTION_EVALUATION_RUN = "evaluation.run"
ACTION_ADMIN_CONFIG = "admin.config"
ACTION_ACCESS_DENIED = "security.access_denied"
ACTION_SCOPE_VIOLATION = "security.scope_violation"
ACTION_INJECTION_DETECTED = "security.prompt_injection_detected"


async def record_audit(
    session: AsyncSession,
    *,
    action: str,
    tenant_id: str,
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    outcome: str = "success",
    ip_address: str | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditLog:
    """Persist an audit row. Never raises: auditing must not break a request."""
    entry = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        request_id=request_id_var.get(),
        ip_address=ip_address,
        detail=detail or {},
    )
    try:
        session.add(entry)
        await session.flush()
    except Exception as exc:  # noqa: BLE001
        logger.warning("audit_write_failed", action=action, error=str(exc))
    return entry


async def record_principal_action(
    session: AsyncSession,
    principal: Principal,
    *,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    outcome: str = "success",
    ip_address: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    await record_audit(
        session,
        action=action,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        ip_address=ip_address,
        detail=detail,
    )


async def recent_audit_entries(
    session: AsyncSession, *, tenant_id: str, limit: int = 100, action: str | None = None
) -> list[AuditLog]:
    statement = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    if action:
        statement = statement.where(AuditLog.action == action)
    statement = statement.order_by(AuditLog.created_at.desc()).limit(min(limit, 500))
    return list((await session.execute(statement)).scalars())
