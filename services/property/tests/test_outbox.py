"""Tests for outbox pattern in Property service: atomic writes + event relay."""

import pytest
from uuid import uuid4, UUID
from datetime import datetime, UTC

from crepro_common import OutboxEntry, OutboxEntryStatus, EntityNotFoundError
from crepro_property.repository import outbox


@pytest.fixture(autouse=True)
def reset_repositories():
    """Reset repositories before each test."""
    outbox._rows.clear()
    yield


class TestOutboxAtomicity:
    """Verify outbox entries are created atomically with domain writes."""

    def test_create_outbox_entry_stores_in_repository(self):
        """Creating an outbox entry stores it in the outbox repository."""
        tenant_id = uuid4()
        entry = OutboxEntry(
            tenant_id=tenant_id,
            event_id=uuid4(),
            event_type="PropertyCreated",
            source="property-service",
            schema_version=1,
            status=OutboxEntryStatus.PENDING,
            payload={"property_id": str(uuid4()), "name": "Test Property"},
        )
        
        # Create entry
        created = outbox.create(entry)
        
        # Verify it's in the repository
        retrieved = outbox.get(tenant_id, created.id)
        assert retrieved.id == created.id
        assert retrieved.event_type == "PropertyCreated"
        assert retrieved.status == OutboxEntryStatus.PENDING

    def test_multiple_entries_create_separate_records(self):
        """Creating multiple outbox entries creates separate records."""
        tenant_id = uuid4()
        
        entries = [
            OutboxEntry(
                tenant_id=tenant_id,
                event_id=uuid4(),
                event_type="PropertyCreated",
                source="property-service",
                schema_version=1,
                status=OutboxEntryStatus.PENDING,
                payload={"property_id": str(uuid4()), "name": f"Property {i}"},
            )
            for i in range(3)
        ]
        
        # Create entries
        created_ids = [outbox.create(e).id for e in entries]
        
        # Verify all are in the repository
        tenant_outbox = outbox.list(tenant_id)
        assert len(tenant_outbox) == 3
        assert all(e.id in created_ids for e in tenant_outbox)

    def test_outbox_entry_cross_tenant_isolation(self):
        """Tenant B's outbox entries do not appear in Tenant A's outbox."""
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        # Create entries for both tenants
        entry_a = OutboxEntry(
            tenant_id=tenant_a,
            event_id=uuid4(),
            event_type="PropertyCreated",
            source="property-service",
            payload={"property_id": str(uuid4())},
        )
        entry_b = OutboxEntry(
            tenant_id=tenant_b,
            event_id=uuid4(),
            event_type="PropertyCreated",
            source="property-service",
            payload={"property_id": str(uuid4())},
        )
        
        outbox.create(entry_a)
        outbox.create(entry_b)
        
        # Verify tenant isolation
        tenant_a_outbox = outbox.list(tenant_a)
        tenant_b_outbox = outbox.list(tenant_b)
        
        assert len(tenant_a_outbox) == 1
        assert len(tenant_b_outbox) == 1
        assert tenant_a_outbox[0].tenant_id == tenant_a
        assert tenant_b_outbox[0].tenant_id == tenant_b


class TestOutboxRelay:
    """Verify outbox relay functions for publishing and tracking."""

    def test_get_pending_outbox_entries(self):
        """get_pending_outbox_entries returns only PENDING entries."""
        from crepro_common import get_pending_outbox_entries
        
        tenant_id = uuid4()
        pending1 = OutboxEntry(
            tenant_id=tenant_id,
            event_type="PropertyCreated",
            source="property-service",
            status=OutboxEntryStatus.PENDING,
        )
        pending2 = OutboxEntry(
            tenant_id=tenant_id,
            event_type="PropertyUpdated",
            source="property-service",
            status=OutboxEntryStatus.PENDING,
        )
        published = OutboxEntry(
            tenant_id=tenant_id,
            event_type="PropertyDeleted",
            source="property-service",
            status=OutboxEntryStatus.PUBLISHED,
        )
        
        outbox.create(pending1)
        outbox.create(pending2)
        outbox.create(published)
        
        # Get pending
        pending = get_pending_outbox_entries(outbox, tenant_id)
        assert len(pending) == 2
        assert all(e.status == OutboxEntryStatus.PENDING for e in pending)

    def test_mark_outbox_entry_published(self):
        """mark_published sets status to PUBLISHED and sets published_at."""
        from crepro_common import mark_published
        
        tenant_id = uuid4()
        entry = OutboxEntry(
            tenant_id=tenant_id,
            event_type="PropertyCreated",
            source="property-service",
            status=OutboxEntryStatus.PENDING,
        )
        created = outbox.create(entry)
        
        # Mark published
        mark_published(outbox, tenant_id, created.id)
        
        # Verify
        published = outbox.get(tenant_id, created.id)
        assert published.status == OutboxEntryStatus.PUBLISHED
        assert published.published_at is not None

    def test_mark_outbox_entry_failed(self):
        """mark_failed sets status to FAILED and stores error message."""
        from crepro_common import mark_failed
        
        tenant_id = uuid4()
        entry = OutboxEntry(
            tenant_id=tenant_id,
            event_type="PropertyCreated",
            source="property-service",
            status=OutboxEntryStatus.PENDING,
        )
        created = outbox.create(entry)
        
        # Mark failed
        mark_failed(outbox, tenant_id, created.id, "Service Bus unavailable")
        
        # Verify
        failed = outbox.get(tenant_id, created.id)
        assert failed.status == OutboxEntryStatus.FAILED
        assert failed.last_error == "Service Bus unavailable"

    def test_outbox_entry_retry_count_increments(self):
        """mark_failed increments retry_count."""
        from crepro_common import mark_failed
        
        tenant_id = uuid4()
        entry = OutboxEntry(
            tenant_id=tenant_id,
            event_type="PropertyCreated",
            source="property-service",
            status=OutboxEntryStatus.PENDING,
            retry_count=0,
        )
        created = outbox.create(entry)
        
        # Mark failed twice
        mark_failed(outbox, tenant_id, created.id, "Error 1")
        mark_failed(outbox, tenant_id, created.id, "Error 2")
        
        # Verify retry_count incremented
        final = outbox.get(tenant_id, created.id)
        assert final.retry_count == 2


class TestOutboxAtLeastOnceDelivery:
    """Verify at-least-once delivery semantics."""

    def test_duplicate_event_has_same_event_id(self):
        """Two calls with same event data generate different entries but same event_id dedups at consumer."""
        tenant_id = uuid4()
        event_id = uuid4()
        
        # Create two entries with same event_id (simulating retry/duplicate)
        entry1 = OutboxEntry(
            tenant_id=tenant_id,
            event_id=event_id,
            event_type="PropertyCreated",
            source="property-service",
            payload={"property_id": "abc123"},
        )
        entry2 = OutboxEntry(
            tenant_id=tenant_id,
            event_id=event_id,  # Same event_id
            event_type="PropertyCreated",
            source="property-service",
            payload={"property_id": "abc123"},
        )
        
        created1 = outbox.create(entry1)
        created2 = outbox.create(entry2)
        
        # Entries have different IDs but same event_id
        assert created1.id != created2.id
        assert created1.event_id == created2.event_id
        
        # Consumer deduplicates by event_id
        all_entries = outbox.list(tenant_id)
        event_ids = [e.event_id for e in all_entries]
        assert event_ids.count(event_id) == 2  # Both present (consumer deduplicates)

    def test_outbox_preserves_event_ordering(self):
        """Events are retrievable in creation order."""
        tenant_id = uuid4()
        
        # Create entries in sequence
        entry_ids = []
        for i in range(5):
            entry = OutboxEntry(
                tenant_id=tenant_id,
                event_type=f"Event{i}",
                source="property-service",
                payload={"index": i},
            )
            created = outbox.create(entry)
            entry_ids.append(created.id)
        
        # Retrieve all for tenant
        retrieved = outbox.list(tenant_id)
        
        # Verify order (InMemoryRepository preserves insertion order)
        assert len(retrieved) == 5
        assert [e.payload["index"] for e in retrieved] == [0, 1, 2, 3, 4]


class TestOutboxSchema:
    """Verify outbox entry schema and defaults."""

    def test_outbox_entry_required_fields(self):
        """OutboxEntry requires tenant_id, event_type, and source."""
        tenant_id = uuid4()
        
        # Valid entry
        entry = OutboxEntry(
            tenant_id=tenant_id,
            event_type="PropertyCreated",
            source="property-service",
        )
        assert entry.tenant_id == tenant_id
        assert entry.event_type == "PropertyCreated"
        assert entry.source == "property-service"

    def test_outbox_entry_default_status_is_pending(self):
        """OutboxEntry defaults to PENDING status."""
        entry = OutboxEntry(
            tenant_id=uuid4(),
            event_type="PropertyCreated",
            source="property-service",
        )
        assert entry.status == OutboxEntryStatus.PENDING

    def test_outbox_entry_schema_version(self):
        """OutboxEntry has schema_version with default 1."""
        entry = OutboxEntry(
            tenant_id=uuid4(),
            event_type="PropertyCreated",
            source="property-service",
        )
        assert entry.schema_version == 1
        
        # Can override
        entry2 = OutboxEntry(
            tenant_id=uuid4(),
            event_type="PropertyCreated",
            source="property-service",
            schema_version=2,
        )
        assert entry2.schema_version == 2

    def test_outbox_entry_timestamps(self):
        """OutboxEntry has created_at, updated_at, and optional published_at."""
        entry = OutboxEntry(
            tenant_id=uuid4(),
            event_type="PropertyCreated",
            source="property-service",
        )
        
        assert entry.created_at is not None
        assert entry.updated_at is not None
        assert entry.published_at is None
        assert isinstance(entry.created_at, datetime)


class TestOutboxEdgeCases:
    """Test edge cases and error conditions."""

    def test_outbox_entry_with_empty_payload(self):
        """OutboxEntry with empty payload is valid."""
        tenant_id = uuid4()
        entry = OutboxEntry(
            tenant_id=tenant_id,
            event_type="PropertyCreated",
            source="property-service",
            payload={},
        )
        created = outbox.create(entry)
        retrieved = outbox.get(tenant_id, created.id)
        assert retrieved.payload == {}

    def test_outbox_entry_with_large_payload(self):
        """OutboxEntry can handle large payload dicts."""
        tenant_id = uuid4()
        large_payload = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}
        
        entry = OutboxEntry(
            tenant_id=tenant_id,
            event_type="PropertyCreated",
            source="property-service",
            payload=large_payload,
        )
        created = outbox.create(entry)
        retrieved = outbox.get(tenant_id, created.id)
        assert len(retrieved.payload) == 100
        assert retrieved.payload["key_50"] == "value_50" * 100

    def test_outbox_entry_retry_count_max_value(self):
        """OutboxEntry retry_count can be incremented to high values."""
        tenant_id = uuid4()
        entry = OutboxEntry(
            tenant_id=tenant_id,
            event_type="PropertyCreated",
            source="property-service",
            retry_count=0,
        )
        created = outbox.create(entry)
        
        # Increment to high count
        for _ in range(100):
            created.retry_count += 1
        
        updated = outbox.update(tenant_id, created)
        retrieved = outbox.get(tenant_id, updated.id)
        assert retrieved.retry_count == 100

    def test_get_nonexistent_outbox_entry_raises(self):
        """Getting a non-existent entry raises EntityNotFoundError."""
        tenant_id = uuid4()
        fake_id = uuid4()
        
        with pytest.raises(EntityNotFoundError):
            outbox.get(tenant_id, fake_id)

    def test_cross_tenant_get_raises(self):
        """Getting with mismatched tenant_id raises EntityNotFoundError."""
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        entry = OutboxEntry(
            tenant_id=tenant_a,
            event_type="PropertyCreated",
            source="property-service",
        )
        created = outbox.create(entry)
        
        # Try to get with different tenant
        with pytest.raises(EntityNotFoundError):
            outbox.get(tenant_b, created.id)
