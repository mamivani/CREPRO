"""Shared JWT issuing and validation (15-day plan, Day 5).

The identity service issues these tokens on login; any service can validate one with
`decode_token` as an eventual alternative to the interim `X-Tenant-Id` header consumed by
`tenancy.require_tenant`. Tokens are signed HS256 with `Settings.jwt_secret`, which every
service shares, so validation never needs a network call to the identity service.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID

import jwt

from crepro_common.config import Settings, get_settings


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class InvalidTokenError(RuntimeError):
    """Raised when a token fails signature, expiry, issuer, or claim validation."""


@dataclass(frozen=True)
class TokenClaims:
    tenant_id: UUID
    user_id: UUID
    role: str
    token_type: TokenType


def issue_token(
    *,
    tenant_id: UUID,
    user_id: UUID,
    role: str,
    token_type: TokenType,
    settings: Settings | None = None,
) -> str:
    settings = settings or get_settings()
    now = datetime.now(UTC)
    ttl_minutes = (
        settings.access_token_ttl_minutes
        if token_type is TokenType.ACCESS
        else settings.refresh_token_ttl_minutes
    )
    payload = {
        "tenantId": str(tenant_id),
        "userId": str(user_id),
        "role": role,
        "type": token_type.value,
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + timedelta(minutes=ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def issue_token_pair(
    *,
    tenant_id: UUID,
    user_id: UUID,
    role: str,
    settings: Settings | None = None,
) -> tuple[str, str]:
    """Issue an (access, refresh) token pair carrying the same tenant/user/role claims."""
    settings = settings or get_settings()
    access = issue_token(
        tenant_id=tenant_id, user_id=user_id, role=role, token_type=TokenType.ACCESS, settings=settings
    )
    refresh = issue_token(
        tenant_id=tenant_id, user_id=user_id, role=role, token_type=TokenType.REFRESH, settings=settings
    )
    return access, refresh


def decode_token(
    token: str,
    *,
    expected_type: TokenType | None = None,
    settings: Settings | None = None,
) -> TokenClaims:
    settings = settings or get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], issuer=settings.jwt_issuer)
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    try:
        claims = TokenClaims(
            tenant_id=UUID(payload["tenantId"]),
            user_id=UUID(payload["userId"]),
            role=payload["role"],
            token_type=TokenType(payload["type"]),
        )
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError("Token is missing required claims") from exc
    if expected_type is not None and claims.token_type is not expected_type:
        raise InvalidTokenError(f"Expected a {expected_type.value} token")
    return claims
