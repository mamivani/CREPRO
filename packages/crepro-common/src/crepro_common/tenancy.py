from collections.abc import AsyncGenerator
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from fastapi import Header


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
    x_tenant_id: UUID = Header(..., alias="X-Tenant-Id"),
) -> AsyncGenerator[TenantContext]:
    """FastAPI dependency that resolves tenant context for a request and binds it for the call's duration.

    Interim tenant resolution until the identity service's JWT middleware is wired in (15-day plan, Day 5);
    routers depend on this rather than reading the header directly so the swap is a one-line change later.
    Must stay an async generator: FastAPI runs sync dependencies in a worker thread, where the enter and
    exit of a context manager can land on different threads and break contextvar token resets.
    """
    token = bind_tenant(TenantContext(tenant_id=x_tenant_id))
    try:
        yield current_tenant()
    finally:
        unbind_tenant(token)
