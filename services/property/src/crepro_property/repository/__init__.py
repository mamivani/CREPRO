"""Tenant-scoped in-memory stores for the property service, ahead of a real database."""

from crepro_common import InMemoryRepository, OutboxEntry
from crepro_property.models import Property, Unit

properties: InMemoryRepository[Property] = InMemoryRepository()
units: InMemoryRepository[Unit] = InMemoryRepository()
outbox: InMemoryRepository[OutboxEntry] = InMemoryRepository()
