"""Tenant-scoped in-memory stores for the lease service, ahead of a real database."""

from crepro_common import InMemoryRepository
from crepro_lease.models import Lease, LeaseCharge, LeaseExit, LeaseIncrementRule, Resident

leases: InMemoryRepository[Lease] = InMemoryRepository()
charges: InMemoryRepository[LeaseCharge] = InMemoryRepository()
increment_rules: InMemoryRepository[LeaseIncrementRule] = InMemoryRepository()
exits: InMemoryRepository[LeaseExit] = InMemoryRepository()
residents: InMemoryRepository[Resident] = InMemoryRepository()
