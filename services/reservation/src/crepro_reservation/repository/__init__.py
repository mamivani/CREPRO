"""Tenant-scoped in-memory store for the reservation service, ahead of a real database."""

from crepro_common import InMemoryRepository
from crepro_reservation.models import Reservation

reservations: InMemoryRepository[Reservation] = InMemoryRepository()
