"""Tests for ERP Adapter push path (Day 11)."""

from uuid import uuid4

import pytest
from crepro_common import EventEnvelope
from crepro_erp_adapter.main import app
from crepro_erp_adapter.push import process_event
from fastapi.testclient import TestClient


class TestProcessEvent:
    """Test event processing from outbox relay."""

    @pytest.mark.asyncio
    async def test_successfully_posts_new_event_to_erp(self, monkeypatch) -> None:
        """Process event: new event is posted to ERP and ledger is updated."""
        tenant_id = uuid4()
        entity_id = uuid4()
        event_id = uuid4()

        event = EventEnvelope(
            event_id=event_id,
            event_type="CustomerCreated",
            source="property",
            tenant_id=tenant_id,
            payload={"name": "New Customer", "platform_id": str(entity_id)},
        )

        # Mock the internal functions
        async def mock_idempotency(tenant_id, entity_id, erp_client, external_doctype):
            return None  # Not posted yet

        async def mock_post(tenant_id, entity_id, erp_client, external_doctype, payload):
            return "CUST-001"  # Successfully posted

        monkeypatch.setattr("crepro_erp_adapter.push.check_idempotency", mock_idempotency)
        monkeypatch.setattr("crepro_erp_adapter.push.post_to_erp", mock_post)

        import httpx
        async with httpx.AsyncClient() as client:
            result = await process_event(event, client)

        assert result is True

    @pytest.mark.asyncio
    async def test_idempotent_replay_returns_existing_record(self, monkeypatch) -> None:
        """Process event: duplicate event returns existing record without reposting."""
        tenant_id = uuid4()
        entity_id = uuid4()
        event_id = uuid4()

        event = EventEnvelope(
            event_id=event_id,
            event_type="CustomerCreated",
            source="property",
            tenant_id=tenant_id,
            payload={"name": "Test Customer", "platform_id": str(entity_id)},
        )

        # Mock: already posted, return existing name
        async def mock_idempotency(tenant_id, entity_id, erp_client, external_doctype):
            return "CUST-001"  # Already exists

        monkeypatch.setattr("crepro_erp_adapter.push.check_idempotency", mock_idempotency)

        import httpx
        async with httpx.AsyncClient() as client:
            result = await process_event(event, client)

        assert result is True

    @pytest.mark.asyncio
    async def test_post_failure_records_failed_state(self, monkeypatch) -> None:
        """Process event: post failure is recorded for retry."""
        tenant_id = uuid4()
        entity_id = uuid4()
        event_id = uuid4()

        event = EventEnvelope(
            event_id=event_id,
            event_type="InvoiceGenerated",
            source="lease",
            tenant_id=tenant_id,
            payload={"invoice_number": "INV-001", "platform_id": str(entity_id)},
        )

        # Mock: not posted, and post fails
        async def mock_idempotency(tenant_id, entity_id, erp_client, external_doctype):
            return None

        async def mock_post(tenant_id, entity_id, erp_client, external_doctype, payload):
            return None  # Post failed

        monkeypatch.setattr("crepro_erp_adapter.push.check_idempotency", mock_idempotency)
        monkeypatch.setattr("crepro_erp_adapter.push.post_to_erp", mock_post)

        import httpx
        async with httpx.AsyncClient() as client:
            result = await process_event(event, client)

        assert result is False


class TestDaprPushEndpoint:
    """Test the Dapr pub/sub push endpoint."""

    def test_endpoint_receives_event_and_processes(self, monkeypatch) -> None:
        """POST /subscribe/erp-events receives event and processes it."""
        client = TestClient(app)
        tenant_id = str(uuid4())
        entity_id = str(uuid4())

        # Simulate Dapr pushing an event
        event = {
            "event_id": str(uuid4()),
            "event_type": "CustomerCreated",
            "source": "property",
            "tenant_id": tenant_id,
            "payload": {"name": "Test Customer", "platform_id": entity_id},
        }

        # Mock process_event to accept (event, erp_client)
        async def mock_process_event(event_env, erp_client):
            return True

        monkeypatch.setattr("crepro_erp_adapter.push.process_event", mock_process_event)

        response = client.post(
            "/subscribe/erp-events",
            json=event,
            headers={"X-Tenant-Id": tenant_id},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True


class TestDuplicateEventIdempotency:
    """Test the critical idempotency guarantee: duplicate events create one record."""

    @pytest.mark.asyncio
    async def test_duplicate_event_id_creates_one_erp_record(self, monkeypatch) -> None:
        """
        Day 11 critical test: process same event twice, only one ERP record posted.

        This is the at-least-once delivery guarantee (Dapr can retry on failure)
        combined with idempotency via platform_id to achieve exactly-once semantics.
        """
        tenant_id = uuid4()
        entity_id = uuid4()
        event_id = uuid4()

        event = EventEnvelope(
            event_id=event_id,
            event_type="InvoiceGenerated",
            source="lease",
            tenant_id=tenant_id,
            payload={"invoice_number": "INV-001", "amount": 1000, "platform_id": str(entity_id)},
        )

        post_count = 0

        async def mock_idempotency_first(tenant_id, entity_id, erp_client, external_doctype):
            return None  # First call: not yet posted

        async def mock_idempotency_second(tenant_id, entity_id, erp_client, external_doctype):
            return "SINV-001"  # Second call: now it exists

        async def mock_post(tenant_id, entity_id, erp_client, external_doctype, payload):
            nonlocal post_count
            post_count += 1
            return "SINV-001"

        import httpx
        async with httpx.AsyncClient() as client:
            # First call: not posted yet, so post
            monkeypatch.setattr("crepro_erp_adapter.push.check_idempotency", mock_idempotency_first)
            monkeypatch.setattr("crepro_erp_adapter.push.post_to_erp", mock_post)
            result1 = await process_event(event, client)
            assert result1 is True

            # Second call: now it exists via idempotency check
            monkeypatch.setattr("crepro_erp_adapter.push.check_idempotency", mock_idempotency_second)
            result2 = await process_event(event, client)
            assert result2 is True

        # Verify only one POST was made to ERP
        assert post_count == 1
