"""Tenant-scoped in-memory store for the identity service, ahead of a real database."""

from uuid import UUID

from crepro_common import InMemoryRepository
from crepro_identity.models import LocalCredential, User

users: InMemoryRepository[User] = InMemoryRepository()


class LocalCredentialStore:
    """In-memory password-hash store for local-account logins, keyed by user id."""

    def __init__(self) -> None:
        self._rows: dict[UUID, LocalCredential] = {}

    def get(self, user_id: UUID) -> LocalCredential | None:
        return self._rows.get(user_id)

    def set(self, credential: LocalCredential) -> LocalCredential:
        self._rows[credential.user_id] = credential
        return credential


credentials = LocalCredentialStore()
