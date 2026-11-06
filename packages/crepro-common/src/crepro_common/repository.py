from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from crepro_common.entities import TenantScopedEntity


class EntityNotFoundError(KeyError):
    """Raised when a lookup by id finds nothing for the given tenant."""


class InMemoryRepository[T: TenantScopedEntity]:
    """Tenant-scoped CRUD store used by service scaffolding ahead of a real database.

    Every read and write is filtered by tenant_id, so one tenant can never see or
    overwrite another tenant's rows, even if a caller passes the wrong id.
    """

    def __init__(self) -> None:
        self._rows: dict[UUID, T] = {}

    def list(self, tenant_id: UUID) -> list[T]:
        return [row for row in self._rows.values() if row.tenant_id == tenant_id]

    def list_all(self) -> list[T]:
        """Every row across every tenant, bypassing tenant scoping.

        Only for internal, non-tenant-facing operations (e.g. the outbox relay
        background task, which must drain pending events for every tenant).
        Never expose this through an HTTP endpoint.
        """
        return list(self._rows.values())

    def get(self, tenant_id: UUID, entity_id: UUID) -> T:
        row = self._rows.get(entity_id)
        if row is None or row.tenant_id != tenant_id:
            raise EntityNotFoundError(str(entity_id))
        return row

    def create(self, entity: T) -> T:
        self._rows[entity.id] = entity
        return entity

    def update(self, tenant_id: UUID, entity: T) -> T:
        self.get(tenant_id, entity.id)  # raises if missing or cross-tenant
        entity.touch()
        self._rows[entity.id] = entity
        return entity

    def delete(self, tenant_id: UUID, entity_id: UUID) -> None:
        self.get(tenant_id, entity_id)  # raises if missing or cross-tenant
        del self._rows[entity_id]

    def seed(self, entities: Iterable[T]) -> None:
        """Test and local-dev helper to preload rows."""
        for entity in entities:
            self._rows[entity.id] = entity
