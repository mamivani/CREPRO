"""JWT token generation, validation, and tenant resolution."""

from datetime import UTC, datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from jose import JWTError, jwt
from pydantic import BaseModel, Field


class TokenClaims(BaseModel):
    """JWT token claims structure."""

    sub: str = Field(..., description="User ID (UUID as string)")
    tenant_id: str = Field(..., description="Tenant ID (UUID as string)")
    role: str = Field(..., description="User role")
    iss: str = Field(..., description="Issuer")
    aud: str = Field(..., description="Audience")
    iat: int = Field(..., description="Issued at (Unix timestamp)")
    exp: int = Field(..., description="Expiration (Unix timestamp)")


class TokenIssuer:
    """Generate and validate JWT tokens."""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        issuer: str = "crepro",
        audience: str = "crepro-api",
        expiration_minutes: int = 60,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience
        self.expiration_minutes = expiration_minutes

    def issue(
        self,
        user_id: UUID,
        tenant_id: UUID,
        role: str,
        expires_in: Optional[timedelta] = None,
    ) -> str:
        """Issue a signed JWT token."""
        now = datetime.now(UTC)
        expires = now + (expires_in or timedelta(minutes=self.expiration_minutes))

        claims = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "role": role,
            "iss": self.issuer,
            "aud": self.audience,
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
        }

        return jwt.encode(claims, self.secret_key, algorithm=self.algorithm)

    def validate(self, token: str) -> TokenClaims:
        """Validate and decode a JWT token. Raises JWTError if invalid."""
        payload = jwt.decode(
            token,
            self.secret_key,
            algorithms=[self.algorithm],
            audience=self.audience,
            issuer=self.issuer,
        )
        return TokenClaims(**payload)


class TenantResolver:
    """Resolve tenant from domain, subdomain, or claim."""

    @staticmethod
    def resolve_from_host(host: str) -> Optional[UUID]:
        """
        Resolve tenant ID from host header.
        Priority: custom_domain > subdomain > None

        Examples:
        - "tenant1.local" -> UUID from subdomain registry
        - "custom.domain.com" -> UUID from domain registry
        """
        # In a full implementation, this would query a domain registry.
        # For now, parse subdomain if it looks like a UUID or known tenant.
        if "." in host:
            parts = host.split(".")
            if len(parts) > 1:
                subdomain = parts[0]
                # Attempt to parse as UUID; if it works, return it
                try:
                    return UUID(subdomain)
                except ValueError:
                    pass
        return None

    @staticmethod
    def resolve_from_header(
        tenant_id_header: Optional[str],
    ) -> Optional[UUID]:
        """Resolve tenant ID from X-Tenant-ID header."""
        if tenant_id_header:
            try:
                return UUID(tenant_id_header)
            except ValueError:
                pass
        return None

    @staticmethod
    def resolve(
        host: Optional[str] = None,
        tenant_id_header: Optional[str] = None,
        tenant_id_claim: Optional[str] = None,
    ) -> Optional[UUID]:
        """
        Resolve tenant ID with priority: custom domain > subdomain > header > claim.
        """
        if host:
            resolved = TenantResolver.resolve_from_host(host)
            if resolved:
                return resolved

        resolved = TenantResolver.resolve_from_header(tenant_id_header)
        if resolved:
            return resolved

        if tenant_id_claim:
            try:
                return UUID(tenant_id_claim)
            except ValueError:
                pass

        return None
