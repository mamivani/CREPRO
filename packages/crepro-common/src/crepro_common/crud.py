from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from crepro_common.entities import TenantScopedEntity
from crepro_common.repository import EntityNotFoundError, InMemoryRepository
from crepro_common.tenancy import TenantContext, require_tenant


def build_crud_router[T: TenantScopedEntity](
    *,
    prefix: str,
    tags: list[str],
    repository: InMemoryRepository[T],
    entity_cls: type[T],
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    not_found_detail: str,
) -> APIRouter:
    """Build a tenant-scoped list/create/get/patch/delete router backed by an InMemoryRepository.

    Every service wires its own entities, schemas and repository into this factory instead of
    hand-writing the same five endpoints, so the CRUD surface and tenant isolation stay identical
    everywhere. Routers can add bespoke endpoints alongside the one this returns.
    """
    router = APIRouter(prefix=prefix, tags=tags)

    @router.get("", response_model=list[entity_cls])
    def list_all(tenant: TenantContext = Depends(require_tenant)) -> list[T]:
        return repository.list(tenant.tenant_id)

    @router.post("", response_model=entity_cls, status_code=status.HTTP_201_CREATED)
    def create(payload: create_schema, tenant: TenantContext = Depends(require_tenant)) -> T:
        entity = entity_cls(tenant_id=tenant.tenant_id, **payload.model_dump())
        return repository.create(entity)

    @router.get("/{entity_id}", response_model=entity_cls)
    def get(entity_id: UUID, tenant: TenantContext = Depends(require_tenant)) -> T:
        try:
            return repository.get(tenant.tenant_id, entity_id)
        except EntityNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, not_found_detail) from exc

    @router.patch("/{entity_id}", response_model=entity_cls)
    def update(
        entity_id: UUID,
        payload: update_schema,
        tenant: TenantContext = Depends(require_tenant),
    ) -> T:
        try:
            existing = repository.get(tenant.tenant_id, entity_id)
        except EntityNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, not_found_detail) from exc
        updated = existing.model_copy(update=payload.model_dump(exclude_unset=True))
        return repository.update(tenant.tenant_id, updated)

    @router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete(entity_id: UUID, tenant: TenantContext = Depends(require_tenant)) -> None:
        try:
            repository.delete(tenant.tenant_id, entity_id)
        except EntityNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, not_found_detail) from exc

    return router
