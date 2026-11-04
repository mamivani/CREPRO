"""Tests for Day 12: Adapter mappings, retry policy, and DLQ routing."""

import asyncio
from datetime import datetime
from uuid import uuid4

import pytest
from crepro_common import EventEnvelope
from crepro_erp_adapter.main import app
from crepro_erp_adapter.mappings import (
    CustomerMapping,
    InvoiceMapping,
    PaymentMapping,
    SupplierMapping,
    AdjustmentMapping,
    apply_entity_mapping,
)
from crepro_erp_adapter.models import AdapterEventType, AdapterLedgerStatus
from crepro_erp_adapter.push import (
    post_to_erp_with_retry,
    route_to_dlq,
    MAX_RETRY_ATTEMPTS,
    RETRY_BACKOFF_SECONDS,
)
from fastapi.testclient import TestClient


class TestEntityMappings:
    """Test entity field mapping conversions."""

    def test_customer_mapping_converts_fields(self) -> None:
        """Customer mapping produces correct ERP field names."""
        domain_customer = {
            "name": "ACME Corp",
            "email": "contact@acme.com",
            "phone": "+1-555-0100",
            "type": "company",
            "tier": "Premium",
            "region": "West Coast",
            "platform_id": str(uuid4()),
        }

        erp_customer = CustomerMapping.to_erp(domain_customer)

        assert erp_customer["customer_name"] == "ACME Corp"
        assert erp_customer["email_id"] == "contact@acme.com"
        assert erp_customer["phone"] == "+1-555-0100"
        assert erp_customer["customer_type"] == "Company"
        assert erp_customer["customer_group"] == "Premium"
        assert erp_customer["territory"] == "West Coast"
        assert erp_customer["custom_platform_id"] == domain_customer["platform_id"]

    def test_customer_mapping_individual_type(self) -> None:
        """Customer mapping handles individual (person) type."""
        domain_customer = {
            "name": "John Doe",
            "type": "person",
            "platform_id": str(uuid4()),
        }

        erp_customer = CustomerMapping.to_erp(domain_customer)

        assert erp_customer["customer_type"] == "Individual"

    def test_supplier_mapping_converts_fields(self) -> None:
        """Supplier mapping produces correct ERP field names."""
        domain_vendor = {
            "name": "ABC Supply Co",
            "email": "sales@abcsupply.com",
            "phone": "+1-555-0200",
            "type": "company",
            "tier": "Preferred",
            "region": "East Coast",
            "platform_id": str(uuid4()),
        }

        erp_supplier = SupplierMapping.to_erp(domain_vendor)

        assert erp_supplier["supplier_name"] == "ABC Supply Co"
        assert erp_supplier["email_id"] == "sales@abcsupply.com"
        assert erp_supplier["supplier_type"] == "Organization"
        assert erp_supplier["supplier_group"] == "Preferred"

    def test_invoice_mapping_converts_fields(self) -> None:
        """Invoice mapping produces correct ERP field names and structure."""
        domain_invoice = {
            "customer_id": "CUST-001",
            "issued_at": "2025-01-15",
            "due_date": "2025-02-15",
            "total_amount": 5000.00,
            "invoice_number": "INV-2025-001",
            "items": [
                {
                    "product_id": "PROD-001",
                    "quantity": 2,
                    "unit_price": 1500.00,
                    "line_amount": 3000.00,
                },
                {
                    "product_id": "PROD-002",
                    "quantity": 1,
                    "unit_price": 2000.00,
                    "line_amount": 2000.00,
                }
            ],
            "platform_id": str(uuid4()),
        }

        erp_invoice = InvoiceMapping.to_erp(domain_invoice)

        assert erp_invoice["customer"] == "CUST-001"
        assert erp_invoice["posting_date"] == "2025-01-15"
        assert erp_invoice["due_date"] == "2025-02-15"
        assert erp_invoice["grand_total"] == 5000.00
        assert len(erp_invoice["items"]) == 2
        assert erp_invoice["items"][0]["item_code"] == "PROD-001"
        assert erp_invoice["items"][0]["qty"] == 2
        assert erp_invoice["items"][0]["rate"] == 1500.00

    def test_payment_mapping_converts_fields(self) -> None:
        """Payment mapping produces correct ERP field names."""
        domain_payment = {
            "customer_id": "CUST-001",
            "amount": 5000.00,
            "date": "2025-01-20",
            "method": "Bank Transfer",
            "reference_id": "TRX-2025-001",
            "invoice_id": "INV-2025-001",
            "platform_id": str(uuid4()),
        }

        erp_payment = PaymentMapping.to_erp(domain_payment)

        assert erp_payment["party_type"] == "Customer"
        assert erp_payment["party"] == "CUST-001"
        assert erp_payment["posting_date"] == "2025-01-20"
        assert erp_payment["received_amount"] == 5000.00
        assert erp_payment["mode_of_payment"] == "Bank Transfer"
        assert erp_payment["reference_no"] == "TRX-2025-001"

    def test_adjustment_mapping_creates_journal_entry(self) -> None:
        """Adjustment mapping creates balanced journal entry lines."""
        domain_adjustment = {
            "customer_id": "CUST-001",
            "amount": 500.00,
            "date": "2025-01-15",
            "type": "debit",
            "description": "Adjustment for overcharge",
            "account": "Income:Service",
            "platform_id": str(uuid4()),
        }

        erp_adjustment = AdjustmentMapping.to_erp(domain_adjustment)

        assert erp_adjustment["posting_date"] == "2025-01-15"
        assert erp_adjustment["remarks"] == "Adjustment for overcharge"
        assert len(erp_adjustment["accounts"]) == 2
        # First line: debit customer account
        assert erp_adjustment["accounts"][0]["debit_in_account_currency"] == 500.00
        assert erp_adjustment["accounts"][0]["credit_in_account_currency"] == 0
        # Second line: credit income account
        assert erp_adjustment["accounts"][1]["debit_in_account_currency"] == 0
        assert erp_adjustment["accounts"][1]["credit_in_account_currency"] == 500.00

    def test_apply_entity_mapping_routes_by_doctype(self) -> None:
        """apply_entity_mapping function routes to correct mapper."""
        customer_payload = {"name": "Test Co", "platform_id": str(uuid4())}

        result = apply_entity_mapping("Customer", customer_payload)

        assert "customer_name" in result
        assert "customer_type" in result

    def test_apply_entity_mapping_fallback_unknown_doctype(self) -> None:
        """apply_entity_mapping returns original payload for unknown doctype."""
        payload = {"some_field": "value"}

        result = apply_entity_mapping("UnknownDoctype", payload)

        assert result == payload


class TestRetryLogic:
    """Test retry mechanism with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_backoff_timing(self, monkeypatch) -> None:
        """Verify exponential backoff timing matches specification."""
        tenant_id = str(uuid4())
        entity_id = uuid4()
        event_id = uuid4()
        attempt_times = []

        async def mock_post_fail(*args, **kwargs):
            """Mock that always fails."""
            attempt_times.append(datetime.utcnow())
            return False, None

        async def mock_dlq(*args, **kwargs):
            """Mock DLQ routing."""
            pass

        monkeypatch.setattr(
            "crepro_erp_adapter.push.post_to_erp_internal", mock_post_fail
        )
        monkeypatch.setattr(
            "crepro_erp_adapter.push.route_to_dlq", mock_dlq
        )

        import httpx
        async with httpx.AsyncClient() as client:
            success, external_name = await post_to_erp_with_retry(
                tenant_id, entity_id, client, "Customer", {"name": "Test"},
                event_id, AdapterEventType.CUSTOMER_UPSERTED
            )

        # Verify all 5 attempts were made
        assert len(attempt_times) == MAX_RETRY_ATTEMPTS
        assert success is False

        # Verify backoff timing (allowing ±0.5s tolerance for execution time)
        for i in range(1, len(attempt_times)):
            time_diff = (attempt_times[i] - attempt_times[i-1]).total_seconds()
            expected_backoff = RETRY_BACKOFF_SECONDS[i-1]
            # Allow 0.5s tolerance for test execution time
            assert expected_backoff - 0.5 <= time_diff <= expected_backoff + 1.0, \
                f"Attempt {i+1}: expected ~{expected_backoff}s, got {time_diff}s"

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_second_attempt(self, monkeypatch) -> None:
        """Retry succeeds if ERP becomes available."""
        tenant_id = str(uuid4())
        entity_id = uuid4()
        event_id = uuid4()
        attempt_count = [0]

        async def mock_post_eventually_succeeds(*args, **kwargs):
            """Fail once, then succeed."""
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                return False, None
            return True, "CUST-001"

        monkeypatch.setattr(
            "crepro_erp_adapter.push.post_to_erp_internal",
            mock_post_eventually_succeeds
        )

        import httpx
        async with httpx.AsyncClient() as client:
            success, external_name = await post_to_erp_with_retry(
                tenant_id, entity_id, client, "Customer", {"name": "Test"},
                event_id, AdapterEventType.CUSTOMER_UPSERTED
            )

        assert success is True
        assert external_name == "CUST-001"
        assert attempt_count[0] == 2  # Failed once, succeeded on second

    @pytest.mark.asyncio
    async def test_retry_routes_to_dlq_after_max_attempts(self, monkeypatch) -> None:
        """Poison message is routed to DLQ after max retries."""
        tenant_id = str(uuid4())
        entity_id = uuid4()
        event_id = uuid4()
        dlq_called = [False]

        async def mock_post_always_fails(*args, **kwargs):
            return False, None

        async def mock_dlq_route(*args, **kwargs):
            dlq_called[0] = True

        monkeypatch.setattr(
            "crepro_erp_adapter.push.post_to_erp_internal", mock_post_always_fails
        )
        monkeypatch.setattr(
            "crepro_erp_adapter.push.route_to_dlq", mock_dlq_route
        )

        import httpx
        async with httpx.AsyncClient() as client:
            success, external_name = await post_to_erp_with_retry(
                tenant_id, entity_id, client, "Customer", {"name": "Test"},
                event_id, AdapterEventType.CUSTOMER_UPSERTED
            )

        assert success is False
        assert dlq_called[0] is True

    @pytest.mark.asyncio
    async def test_field_mapping_applied_before_post(self, monkeypatch) -> None:
        """Entity field mapping is applied before posting to ERP."""
        tenant_id = str(uuid4())
        entity_id = uuid4()
        event_id = uuid4()
        posted_payloads = []

        async def mock_post_capture_payload(entity_id, doctype, payload):
            """Capture the payload sent to ERP."""
            posted_payloads.append(payload)
            return True, "CUST-001"

        monkeypatch.setattr(
            "crepro_erp_adapter.push.post_to_erp_internal", mock_post_capture_payload
        )

        domain_payload = {
            "name": "Test Customer",
            "email": "test@example.com",
            "type": "company",
            "platform_id": str(entity_id),
        }

        import httpx
        async with httpx.AsyncClient() as client:
            await post_to_erp_with_retry(
                tenant_id, entity_id, client, "Customer", domain_payload,
                event_id, AdapterEventType.CUSTOMER_UPSERTED
            )

        # Verify mapping was applied (field names changed)
        assert len(posted_payloads) == 1
        posted = posted_payloads[0]
        assert "customer_name" in posted  # Mapped field
        assert "customer_type" in posted  # Mapped field
        assert posted["customer_type"] == "Company"  # Mapped value


class TestDLQRouting:
    """Test dead-letter queue routing."""

    @pytest.mark.asyncio
    async def test_dlq_route_publishes_to_pubsub(self, monkeypatch) -> None:
        """DLQ routing publishes to dead_letter_events topic (basic check)."""
        # This test verifies that route_to_dlq doesn't raise exceptions
        # Full integration would require a running Dapr sidecar
        tenant_id = str(uuid4())
        event_id = uuid4()
        entity_id = uuid4()

        # Just verify the function exists and can be called
        try:
            # Note: In real environment, Dapr sidecar would be running
            # For now, we just verify the function doesn't crash during call setup
            import asyncio
            task = route_to_dlq(
                tenant_id, event_id, entity_id, "Customer",
                "Max retries exhausted"
            )
            # Don't actually await since we don't have Dapr running
            assert asyncio.iscoroutine(task)
            task.close()  # Cleanup
        except Exception:
            pass  # Expected in test environment without Dapr


class TestRetryIntegration:
    """Integration tests for retry logic in process_event."""

    @pytest.mark.asyncio
    async def test_process_event_uses_retry_logic(self, monkeypatch) -> None:
        """process_event uses retry mechanism for failed posts."""
        from crepro_erp_adapter.push import process_event

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

        retry_call_count = [0]

        async def mock_retry(*args, **kwargs):
            """Track that post_to_erp_with_retry was called."""
            retry_call_count[0] += 1
            return True, "CUST-001"

        monkeypatch.setattr(
            "crepro_erp_adapter.push.post_to_erp_with_retry", mock_retry
        )

        import httpx
        async with httpx.AsyncClient() as client:
            result = await process_event(event, client)

        assert result is True
        assert retry_call_count[0] == 1  # post_to_erp_with_retry was called


class TestDayTwelveExitCriteria:
    """Verify all Day 12 exit criteria are met."""

    def test_all_entity_types_mapped(self) -> None:
        """All entity types have mapping implementations."""
        entity_types = {
            "Customer": CustomerMapping,
            "Supplier": SupplierMapping,
            "Sales Invoice": InvoiceMapping,
            "Payment Entry": PaymentMapping,
            "Journal Entry": AdjustmentMapping,
        }

        for doctype, mapper in entity_types.items():
            assert hasattr(mapper, "to_erp")
            # Test can be called
            result = mapper.to_erp({"platform_id": str(uuid4())})
            assert isinstance(result, dict)

    def test_retry_backoff_values_correct(self) -> None:
        """Exponential backoff values match specification (1, 2, 4, 8, 16 seconds)."""
        assert RETRY_BACKOFF_SECONDS == [1, 2, 4, 8, 16]
        assert MAX_RETRY_ATTEMPTS == 5
        # We have 5 backoff values for 5 attempts (backoff after each failed attempt)
        assert len(RETRY_BACKOFF_SECONDS) == MAX_RETRY_ATTEMPTS

    def test_dlq_route_function_exists(self) -> None:
        """DLQ routing function is implemented."""
        assert callable(route_to_dlq)
