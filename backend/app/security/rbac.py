"""Authorization policy.

Enforced server-side on every request. The frontend may hide buttons, but hiding
never grants or denies anything — every endpoint checks a permission here, and
every retrieval query is filtered by tenant *before* it can reach a model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.db.models.tenancy import ACCESS_LEVELS, ROLES
from app.core.errors import AuthorizationError

#: Permission strings used by API dependencies and tool guards.
PERM_QUERY = "query:run"
PERM_DOCUMENTS_READ = "documents:read"
PERM_DOCUMENTS_WRITE = "documents:write"
PERM_DOCUMENTS_DELETE = "documents:delete"
PERM_SUPPLIERS_READ = "suppliers:read"
PERM_SUPPLIERS_WRITE = "suppliers:write"
PERM_CONTRACTS_READ = "contracts:read"
PERM_CONTRACTS_WRITE = "contracts:write"
PERM_COMPARE = "compare:run"
PERM_EVALUATION_READ = "evaluation:read"
PERM_EVALUATION_RUN = "evaluation:run"
PERM_ADMIN_READ = "admin:read"
PERM_ADMIN_WRITE = "admin:write"
PERM_GRAPH_READ = "graph:read"
PERM_SQL_READ = "structured:read"
PERM_AUDIT_READ = "audit:read"

ALL_PERMISSIONS: frozenset[str] = frozenset(
    {
        PERM_QUERY,
        PERM_DOCUMENTS_READ,
        PERM_DOCUMENTS_WRITE,
        PERM_DOCUMENTS_DELETE,
        PERM_SUPPLIERS_READ,
        PERM_SUPPLIERS_WRITE,
        PERM_CONTRACTS_READ,
        PERM_CONTRACTS_WRITE,
        PERM_COMPARE,
        PERM_EVALUATION_READ,
        PERM_EVALUATION_RUN,
        PERM_ADMIN_READ,
        PERM_ADMIN_WRITE,
        PERM_GRAPH_READ,
        PERM_SQL_READ,
        PERM_AUDIT_READ,
    }
)

READ_ONLY_SHARED = frozenset(
    {PERM_QUERY, PERM_DOCUMENTS_READ, PERM_SUPPLIERS_READ, PERM_CONTRACTS_READ}
)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": ALL_PERMISSIONS,
    "procurement_manager": frozenset(
        {
            *READ_ONLY_SHARED,
            PERM_DOCUMENTS_WRITE,
            PERM_SUPPLIERS_WRITE,
            PERM_CONTRACTS_WRITE,
            PERM_COMPARE,
            PERM_EVALUATION_READ,
            PERM_EVALUATION_RUN,
            PERM_ADMIN_READ,
            PERM_GRAPH_READ,
            PERM_SQL_READ,
            PERM_AUDIT_READ,
        }
    ),
    "buyer": frozenset({*READ_ONLY_SHARED, PERM_COMPARE, PERM_SQL_READ}),
    "compliance": frozenset({*READ_ONLY_SHARED, PERM_COMPARE, PERM_EVALUATION_READ, PERM_ADMIN_READ, PERM_GRAPH_READ}),
    "viewer": READ_ONLY_SHARED,
}

#: Highest document access level each role may read.
ROLE_ACCESS_CEILING: dict[str, str] = {
    "admin": "restricted",
    "procurement_manager": "confidential",
    "compliance": "confidential",
    "buyer": "internal",
    "viewer": "internal",
}


def access_rank(level: str) -> int:
    try:
        return ACCESS_LEVELS.index(level)
    except ValueError:
        # Unknown levels are treated as the most restrictive so a typo can never
        # widen access.
        return len(ACCESS_LEVELS)


@dataclass(frozen=True, slots=True)
class Principal:
    """Authenticated caller context. Threaded through every service call."""

    user_id: str
    tenant_id: str
    email: str
    role: str
    full_name: str = ""
    is_synthetic_allowed: bool = True
    extra_permissions: frozenset[str] = field(default_factory=frozenset)

    @property
    def permissions(self) -> frozenset[str]:
        return ROLE_PERMISSIONS.get(self.role, frozenset()) | self.extra_permissions

    @property
    def access_ceiling(self) -> str:
        return ROLE_ACCESS_CEILING.get(self.role, "public")

    @property
    def readable_access_levels(self) -> list[str]:
        ceiling = access_rank(self.access_ceiling)
        return [level for level in ACCESS_LEVELS if access_rank(level) <= ceiling]

    def can(self, permission: str) -> bool:
        return permission in self.permissions

    def require(self, permission: str) -> None:
        if not self.can(permission):
            raise AuthorizationError(
                f"Role '{self.role}' lacks permission '{permission}'.",
                details={"required_permission": permission, "role": self.role},
            )

    def can_read_level(self, level: str) -> bool:
        return access_rank(level) <= access_rank(self.access_ceiling)

    def as_dict(self) -> dict[str, object]:
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "email": self.email,
            "role": self.role,
            "full_name": self.full_name,
            "permissions": sorted(self.permissions),
            "access_ceiling": self.access_ceiling,
        }


def role_exists(role: str) -> bool:
    return role in ROLES
