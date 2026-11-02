"""Tenant resolution for login requests: custom domain > subdomain > claim
(15-day plan, Day 5).

The identity service does not keep its own copy of the tenant directory - the tenant
service owns `subdomain`/`custom_domain` (services/tenant/.../models/__init__.py) and
exposes `GET /api/v1/tenants/resolve`. `TenantDirectoryClient` is a thin wrapper over that
endpoint so it can be swapped for a fake in tests without a live tenant service.
"""

from uuid import UUID

import httpx
from crepro_common import get_settings


class TenantResolutionError(RuntimeError):
    """Raised when a request's Host header and tenant claim don't resolve to any tenant."""


class TenantDirectoryClient:
    def __init__(self, base_url: str | None = None, *, client: httpx.Client | None = None) -> None:
        base_url = base_url or get_settings().tenant_service_url
        self._client = client or httpx.Client(base_url=base_url, timeout=5.0)

    def resolve_by_host(self, host: str) -> UUID | None:
        response = self._client.get("/api/v1/tenants/resolve", params={"host": host})
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return UUID(response.json()["id"])


def resolve_tenant(
    *,
    host: str | None,
    claimed_tenant_id: UUID | None,
    directory: TenantDirectoryClient,
) -> UUID:
    if host:
        tenant_id = directory.resolve_by_host(host)
        if tenant_id is not None:
            return tenant_id
    if claimed_tenant_id is not None:
        return claimed_tenant_id
    raise TenantResolutionError("Could not resolve a tenant from the request's Host header or tenant_id")
