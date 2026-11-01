"""OAuth2/OIDC integration for multiple identity providers."""

from datetime import UTC, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Provider(str, Enum):
    """Supported identity providers."""

    MICROSOFT = "microsoft"
    GOOGLE = "google"
    APPLE = "apple"
    LOCAL = "local"


class TokenRequest(BaseModel):
    """Base request for token endpoint."""

    code: str = Field(..., description="Authorization code from IdP or password for local")
    redirect_uri: Optional[str] = Field(
        None, description="Redirect URI used in authorization request (required for OAuth)"
    )


class LocalAuthRequest(BaseModel):
    """Local authentication request."""

    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")
    tenant_id: Optional[str] = Field(
        None, description="Tenant ID (UUID), optional for local auth"
    )


class TokenResponse(BaseModel):
    """Token endpoint response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Expiration in seconds")
    refresh_token: Optional[str] = Field(None, description="Refresh token")


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str = Field(..., description="Refresh token")


class OAuthConfig(BaseModel):
    """OAuth2/OIDC provider configuration."""

    client_id: str
    client_secret: str
    authority: str  # e.g., https://login.microsoftonline.com/common or https://accounts.google.com
    token_endpoint: str
    authorize_endpoint: str
    userinfo_endpoint: str
    scopes: list[str] = Field(default_factory=lambda: ["openid", "profile", "email"])


class FederatedIdentity(BaseModel):
    """External federated identity linked to a user."""

    id: UUID
    user_id: UUID
    tenant_id: UUID
    provider: Provider
    provider_user_id: str  # Sub claim or equivalent
    provider_email: Optional[str] = None
    last_login: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
