from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Literal
from uuid import UUID


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
