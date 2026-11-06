from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from crepro_common.entities import TenantScopedEntity
from crepro_common.models import OutboxEntry
from crepro_common.outbox import create_outbox_entry
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
    outbox: InMemoryRepository[OutboxEntry] | None = None,
    outbox_event_type: str | None = None,
    outbox_source: str | None = None,
) -> APIRouter:
    """Build a tenant-scoped list/create/get/patch/delete router backed by an InMemoryRepository.

    Every service wires its own entities, schemas and repository into this factory instead of
    hand-writing the same five endpoints, so the CRUD surface and tenant isolation stay identical
    everywhere. Routers can add bespoke endpoints alongside the one this returns.

    When `outbox`, `outbox_event_type` and `outbox_source` are all given, a successful create
    also writes a PENDING OutboxEntry (payload = the created entity, plus `platform_id` for the
    ERP adapter's idempotency key) so the service's outbox relay delivers it downstream.
    """
    router = APIRouter(prefix=prefix, tags=tags)
    emit_outbox = outbox is not None and outbox_event_type is not None and outbox_source is not None

    @router.get("", response_model=list[entity_cls])
    def list_all(tenant: TenantContext = Depends(require_tenant)) -> list[T]:
        return repository.list(tenant.tenant_id)

    @router.post("", response_model=entity_cls, status_code=status.HTTP_201_CREATED)
    def create(payload: create_schema, tenant: TenantContext = Depends(require_tenant)) -> T:
        entity = entity_cls(tenant_id=tenant.tenant_id, **payload.model_dump())
        created = repository.create(entity)
        if emit_outbox:
            entry = create_outbox_entry(
                tenant_id=tenant.tenant_id,
                event_type=outbox_event_type,
                source=outbox_source,
                payload={**created.model_dump(mode="json"), "platform_id": str(created.id)},
            )
            outbox.create(entry)
        return created

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
