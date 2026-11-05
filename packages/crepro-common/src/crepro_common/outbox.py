"""Outbox pattern implementation for event publishing.

The outbox pattern ensures events are published atomically with domain entity writes:
1. Domain write + outbox row in same transaction
2. Relay picks up pending outbox entries
3. Publishes to message broker (Dapr/Service Bus)
4. Marks entries as PUBLISHED
5. At-least-once delivery semantics (idempotency via event_id)
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from crepro_common.models import OutboxEntry, OutboxEntryStatus
from crepro_common.repository import InMemoryRepository


def create_outbox_entry(
    tenant_id: UUID,
    event_type: str,
    source: str,
    payload: dict[str, Any],
    schema_version: int = 1,
) -> OutboxEntry:
    """Create an outbox entry for an event to be published later.

    Args:
        tenant_id: Tenant that owns this event
        event_type: Type of event (e.g., "PropertyCreated", "LeaseExecuted")
        source: Service that generated the event (e.g., "property-service")
        payload: Event data (will be included in EventEnvelope)
        schema_version: Event schema version (default 1)

    Returns:
        OutboxEntry ready to be persisted
    """
    return OutboxEntry(
        tenant_id=tenant_id,
        event_type=event_type,
        source=source,
        schema_version=schema_version,
        status=OutboxEntryStatus.PENDING,
        payload=payload,
    )


def get_pending_outbox_entries(
    outbox: InMemoryRepository[OutboxEntry],
    tenant_id: UUID,
    limit: int = 100,
) -> list[OutboxEntry]:
    """Get pending outbox entries for a tenant ready for publishing.

    Args:
        outbox: Outbox repository
        tenant_id: Tenant to filter by
        limit: Max entries to return

    Returns:
        List of pending outbox entries for the tenant, in creation order
    """
    all_entries = outbox.list(tenant_id)
    pending = [entry for entry in all_entries if entry.status == OutboxEntryStatus.PENDING]
    return pending[:limit]


def mark_published(
    outbox: InMemoryRepository[OutboxEntry],
    tenant_id: UUID,
    entry_id: UUID,
) -> None:
    """Mark an outbox entry as published.

    Args:
        outbox: Outbox repository
        tenant_id: Tenant that owns the entry
        entry_id: ID of entry to mark published
    """
    entry = outbox.get(tenant_id, entry_id)
    entry.status = OutboxEntryStatus.PUBLISHED
    entry.published_at = datetime.now(UTC)
    entry.touch()
    outbox.update(tenant_id, entry)


def mark_failed(
    outbox: InMemoryRepository[OutboxEntry],
    tenant_id: UUID,
    entry_id: UUID,
    error: str,
) -> None:
    """Mark an outbox entry as failed and increment retry count.

    Args:
        outbox: Outbox repository
        tenant_id: Tenant that owns the entry
        entry_id: ID of entry to mark failed
        error: Error message
    """
    entry = outbox.get(tenant_id, entry_id)
    entry.status = OutboxEntryStatus.FAILED
    entry.last_error = error
    entry.retry_count += 1
    entry.touch()
    outbox.update(tenant_id, entry)
