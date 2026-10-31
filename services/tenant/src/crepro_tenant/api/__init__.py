"""HTTP routes for the tenant service: the control-plane tenant directory.

These endpoints are not tenant-scoped like other services' routes: they manage the
directory of tenants itself, so they take no X-Tenant-Id header.
"""

from uuid import UUID

from crepro_common import EntityNotFoundError
from crepro_tenant.models import Tenant
from crepro_tenant.repository import tenants
from crepro_tenant.schemas import TenantCreate, TenantUpdate
from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


@router.get("", response_model=list[Tenant])
def list_tenants() -> list[Tenant]:
    return tenants.list()


@router.post("", response_model=Tenant, status_code=status.HTTP_201_CREATED)
def create_tenant(payload: TenantCreate) -> Tenant:
    return tenants.create(Tenant(**payload.model_dump()))


@router.get("/{tenant_id}", response_model=Tenant)
def get_tenant(tenant_id: UUID) -> Tenant:
    try:
        return tenants.get(tenant_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found") from exc


@router.patch("/{tenant_id}", response_model=Tenant)
def update_tenant(tenant_id: UUID, payload: TenantUpdate) -> Tenant:
    try:
        existing = tenants.get(tenant_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found") from exc
    updated = existing.model_copy(update=payload.model_dump(exclude_unset=True))
    return tenants.update(updated)


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(tenant_id: UUID) -> None:
    try:
        tenants.delete(tenant_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found") from exc
