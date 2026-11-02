"""API request/response DTOs for the identity service."""

from uuid import UUID

from crepro_identity.models import UserRole, UserStatus
from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    full_name: str
    role: UserRole


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    status: UserStatus | None = None


class OAuthLoginRequest(BaseModel):
    """Body for POST /api/v1/auth/{microsoft,google,apple}."""

    id_token: str
    # Fallback tenant claim for callers with no resolvable Host header (e.g. native/mobile
    # clients). Ignored when the Host header resolves to a tenant (custom domain > subdomain).
    tenant_id: UUID | None = None


class LocalRegisterRequest(BaseModel):
    email: str
    full_name: str
    password: str
    role: UserRole = UserRole.PROPERTY_MANAGER
    tenant_id: UUID | None = None


class LocalLoginRequest(BaseModel):
    email: str
    password: str
    tenant_id: UUID | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
