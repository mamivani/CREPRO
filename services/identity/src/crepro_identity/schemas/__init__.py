"""API request/response DTOs for the identity service."""

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


class LocalAuthRequest(BaseModel):
    """Local authentication with email and password."""

    email: str
    password: str
    tenant_id: str | None = None


class TokenResponse(BaseModel):
    """Token endpoint response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str

