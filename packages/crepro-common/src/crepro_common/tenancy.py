from collections.abc import AsyncGenerator
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from fastapi import Header, HTTPException, status

from crepro_common.security import InvalidTokenError, TokenType, decode_token


class TenantNotSetError(RuntimeError):
    """Raised when code needing tenant data runs without a bound tenant."""


@dataclass(frozen=True)
class TenantContext:
    tenant_id: UUID
    # shared: rows carry tenant_id in a shared database. dedicated: own database and storage.
    tier: Literal["shared", "dedicated"] = "shared"


_tenant: ContextVar[TenantContext | None] = ContextVar("crepro_tenant", default=None)


def bind_tenant(ctx: TenantContext) -> Token[TenantContext | None]:
    return _tenant.set(ctx)


def unbind_tenant(token: Token[TenantContext | None]) -> None:
    _tenant.reset(token)


def current_tenant() -> TenantContext:
    ctx = _tenant.get()
    if ctx is None:
        raise TenantNotSetError("No tenant context is bound to this request")
    return ctx


async def require_tenant(
    x_tenant_id: UUID | None = Header(None, alias="X-Tenant-Id"),
    authorization: str | None = Header(None),
) -> AsyncGenerator[TenantContext]:
    """FastAPI dependency that resolves tenant context for a request and binds it for the call's duration.

    Reads tenant context from a CREPRO access token's `Authorization: Bearer <token>` header when
    present - the identity service's JWT middleware, wired in (15-day plan, Day 5) - falling back
    to the interim `X-Tenant-Id` header otherwise, so every route that already depends on this
    keeps working unchanged until it is ready to require a token.
    Must stay an async generator: FastAPI runs sync dependencies in a worker thread, where the enter and
    exit of a context manager can land on different threads and break contextvar token resets.
    """
    if authorization is not None:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "Expected an 'Authorization: Bearer <token>' header"
            )
        try:
            claims = decode_token(token, expected_type=TokenType.ACCESS)
        except InvalidTokenError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
        tenant_id = claims.tenant_id
    elif x_tenant_id is not None:
        tenant_id = x_tenant_id
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing X-Tenant-Id or Authorization header")

    token_handle = bind_tenant(TenantContext(tenant_id=tenant_id))
    try:
        yield current_tenant()
    finally:
        unbind_tenant(token_handle)
