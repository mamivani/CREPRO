"""Tenant-scoped in-memory stores for the utility service, ahead of a real database."""

from crepro_common import InMemoryRepository
from crepro_utility.models import Meter, MeterReading

meters: InMemoryRepository[Meter] = InMemoryRepository()
readings: InMemoryRepository[MeterReading] = InMemoryRepository()
