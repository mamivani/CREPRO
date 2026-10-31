"""In-memory tenant directory store, ahead of a real database.

Unlike every other service's repository, this one is not itself scoped by tenant_id:
it is the directory that defines which tenant_ids exist, so it cannot reuse
crepro_common's tenant-scoped InMemoryRepository.
"""

from uuid import UUID

from crepro_common import EntityNotFoundError
from crepro_tenant.models import Tenant


class TenantDirectory:
    def __init__(self) -> None:
        self._rows: dict[UUID, Tenant] = {}

    def list(self) -> list[Tenant]:
        return list(self._rows.values())

    def get(self, tenant_id: UUID) -> Tenant:
        row = self._rows.get(tenant_id)
        if row is None:
            raise EntityNotFoundError(str(tenant_id))
        return row

    def create(self, tenant: Tenant) -> Tenant:
        self._rows[tenant.id] = tenant
        return tenant

    def update(self, tenant: Tenant) -> Tenant:
        self.get(tenant.id)  # raises if missing
        tenant.touch()
        self._rows[tenant.id] = tenant
        return tenant

    def delete(self, tenant_id: UUID) -> None:
        self.get(tenant_id)  # raises if missing
        del self._rows[tenant_id]


tenants = TenantDirectory()
