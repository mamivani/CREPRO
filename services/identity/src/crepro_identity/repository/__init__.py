"""Tenant-scoped in-memory store for the identity service, ahead of a real database."""

from crepro_common import InMemoryRepository
from crepro_identity.models import User

users: InMemoryRepository[User] = InMemoryRepository()
