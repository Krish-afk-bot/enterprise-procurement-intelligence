"""Authentication schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import APIModel
from app.schemas.email import EmailAddress


class LoginRequest(APIModel):
    email: EmailAddress
    password: str = Field(min_length=1, max_length=256)
    tenant_slug: str | None = None


class RegisterRequest(APIModel):
    email: EmailAddress
    password: str = Field(min_length=8, max_length=256)
    full_name: str = Field(default="", max_length=255)
    tenant_slug: str | None = None


class RefreshRequest(APIModel):
    refresh_token: str


class UserOut(APIModel):
    id: str
    email: str
    full_name: str
    role: str
    tenant_id: str
    is_active: bool
    last_login_at: datetime | None = None
    permissions: list[str] = Field(default_factory=list)
    access_ceiling: str = "internal"


class TokenResponse(APIModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime
    refresh_expires_at: datetime | None = None
    user: UserOut


class RoleOut(APIModel):
    role: str
    permissions: list[str]
    access_ceiling: str
