from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TenantScopedEntity(BaseModel):
    """Base for every domain entity. Every row in every service carries a tenant_id for isolation."""

    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        """Refresh updated_at. Call before persisting a mutation."""
        self.updated_at = datetime.now(UTC)
