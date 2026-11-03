"""Outbox entry model for event publishing."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from crepro_common.entities import TenantScopedEntity


class OutboxEntryStatus(StrEnum):
    """Status of an outbox entry."""

    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"


class OutboxEntry(TenantScopedEntity):
    """Outbox pattern entry: event that needs to be published to message broker.

    Persisted in the same transaction as the domain entity write.
    Relay picks these up and publishes to Service Bus topics.
    Marked PUBLISHED after successful delivery.
    """

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    source: str
    schema_version: int = 1
    status: OutboxEntryStatus = OutboxEntryStatus.PENDING
    payload: dict[str, Any] = Field(default_factory=dict)
    published_at: datetime | None = None
    retry_count: int = 0
    last_error: str | None = None
