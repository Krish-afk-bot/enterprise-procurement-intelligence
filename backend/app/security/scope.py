"""Authorization scoping for retrieval.

Every vector, sparse, SQL and graph query must be built through these helpers so
that an unauthorized document can never enter a context window, a citation list
or an aggregate (PRD s.44).
"""

from __future__ import annotations

from typing import Any

from app.security.rbac import Principal


def build_retrieval_filters(principal: Principal, **extra: Any) -> dict[str, Any]:
    """Filter document for tenant + readable access levels + caller constraints.

    ``extra`` values override nothing security-related: tenant_id and
    access_level are always applied last.
    """
    filters: dict[str, Any] = {}
    for key, value in extra.items():
        if value is None:
            continue
        filters[key] = value
    filters["tenant_id"] = principal.tenant_id
    filters["access_level"] = {"$in": principal.readable_access_levels}
    return filters


def apply_scope(filters: dict[str, Any] | None, principal: Principal) -> dict[str, Any]:
    """Force scope onto an existing filter document (used by tools/agents)."""
    scoped = dict(filters or {})
    scoped["tenant_id"] = principal.tenant_id
    existing = scoped.get("access_level")
    allowed = set(principal.readable_access_levels)
    if isinstance(existing, dict) and "$in" in existing:
        intersection = [level for level in existing["$in"] if level in allowed]
        scoped["access_level"] = {"$in": intersection}
    elif isinstance(existing, str):
        scoped["access_level"] = existing if existing in allowed else {"$in": []}
    else:
        scoped["access_level"] = {"$in": sorted(allowed)}
    return scoped


def scope_sql_access_levels(principal: Principal) -> list[str]:
    return principal.readable_access_levels


def describe_scope(principal: Principal) -> dict[str, Any]:
    """Safe-to-log description of the effective scope (used in traces)."""
    return {
        "tenant_id": principal.tenant_id,
        "role": principal.role,
        "access_levels": principal.readable_access_levels,
    }
