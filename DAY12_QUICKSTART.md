# Day 12 Quick Start: Adapter Mappings & Retry Policy

**Previous Work:** Day 11 complete with push path and idempotency ✅  
**Branch to Start From:** `feature/day9-backfill-tests`  
**Estimated Time:** 2-3 days  

## What You're Building

Day 12 adds three capabilities to the Day 11 push path:

1. **Entity Field Mappings** - Map domain entity fields to ERP fields
2. **Retry Logic** - Automatic retry with exponential backoff (5 attempts max)
3. **Dead-Letter Queue** - Route poison messages for manual repair

## Architecture Overview

```
Event from Dapr
  ↓
[Day 11] process_event() - Parse, map, check idempotency ✅ DONE
  ↓
[Day 12] post_to_erp_with_retry() - NEW
  ├─ Attempt 1: POST to ERP
  ├─ On failure, update ledger (attempts++) and backoff
  ├─ Attempt 2-5: Retry with exponential backoff (1s, 2s, 4s, 8s, 16s)
  ├─ After attempt 5: Mark FAILED, route to DLQ
  └─ On success: Mark POSTED
  ↓
[Day 13] Reconciliation job picks up FAILED entries and re-retries them
```

## Implementation Tasks

### 1. Complete Entity Field Mappings

**File:** Create `services/erp_adapter/src/crepro_erp_adapter/mappings.py`

```python
from dataclasses import dataclass
from uuid import UUID


@dataclass
class CustomerMapping:
    """Map domain Customer to ERP Customer."""

    def to_erp(customer: dict) -> dict:
        """Convert domain customer fields to ERP format."""
        return {
            "name": customer.get("name"),
            "email": customer.get("email"),
            "phone": customer.get("phone"),
            "customer_type": "Individual" if customer.get("type") == "person" else "Company",
            "customer_group": customer.get("tier", "Gold"),
            "territory": customer.get("region"),
            "custom_platform_id": customer.get("platform_id"),
        }


@dataclass
class InvoiceMapping:
    """Map domain Invoice to ERP Sales Invoice."""

    def to_erp(invoice: dict) -> dict:
        """Convert domain invoice fields to ERP format."""
        return {
            "customer": invoice.get("customer_id"),  # Links to Customer
            "posting_date": invoice.get("issued_at"),
            "due_date": invoice.get("due_date"),
            "total": invoice.get("total_amount"),
            "items": [
                {
                    "item_code": item.get("product_id"),
                    "qty": item.get("quantity"),
                    "rate": item.get("unit_price"),
                    "amount": item.get("line_amount"),
                }
                for item in invoice.get("items", [])
            ],
            "custom_platform_id": invoice.get("platform_id"),
        }


@dataclass
class PaymentMapping:
    """Map domain Payment to ERP Payment Entry."""

    def to_erp(payment: dict) -> dict:
        """Convert domain payment fields to ERP format."""
        return {
            "party_type": "Customer",
            "party": payment.get("customer_id"),
            "posting_date": payment.get("date"),
            "mode_of_payment": payment.get("method"),  # e.g., "Cash", "Bank Transfer"
            "received_amount": payment.get("amount"),
            "reference_no": payment.get("reference_id"),
            "custom_platform_id": payment.get("platform_id"),
            # Link to invoice if provided
            "invoice": payment.get("invoice_id") if payment.get("invoice_id") else None,
        }
```

### 2. Implement Retry with Exponential Backoff

**File:** Modify `services/erp_adapter/src/crepro_erp_adapter/push.py`

Add new function:

```python
import asyncio
from crepro_erp_adapter.mappings import CustomerMapping, InvoiceMapping, PaymentMapping


async def post_to_erp_with_retry(
    tenant_id: str,
    entity_id: UUID,
    erp_client: httpx.AsyncClient,
    external_doctype: str,
    payload: dict,
    max_attempts: int = 5,
) -> tuple[bool, str | None]:
    """
    Post to ERP with exponential backoff retry.

    Returns (success, external_name).
    On max attempts, updates ledger to FAILED and returns (False, None).
    """
    backoff_times = [1, 2, 4, 8, 16]  # seconds

    for attempt in range(1, max_attempts + 1):
        try:
            # Apply entity-specific mapping
            mapped_payload = _apply_entity_mapping(external_doctype, payload)

            # Try to post
            success, external_name = await post_to_erp_internal(entity_id, external_doctype, mapped_payload)

            if success:
                return success, external_name

            # Update ledger with attempt count
            _update_ledger_attempt(tenant_id, entity_id, attempt, f"Attempt {attempt} failed")

            if attempt < max_attempts:
                # Wait before retry
                await asyncio.sleep(backoff_times[attempt - 1])

        except Exception as exc:
            logger.error(f"Attempt {attempt} failed: {exc}")
            _update_ledger_attempt(tenant_id, entity_id, attempt, f"Attempt {attempt} failed: {str(exc)}")

            if attempt < max_attempts:
                await asyncio.sleep(backoff_times[attempt - 1])

    # All retries exhausted
    return False, None


def _apply_entity_mapping(external_doctype: str, payload: dict) -> dict:
    """Apply domain-to-ERP field mapping based on doctype."""
    mapping_map = {
        "Customer": CustomerMapping.to_erp,
        "Supplier": CustomerMapping.to_erp,  # Same structure for now
        "Sales Invoice": InvoiceMapping.to_erp,
        "Payment Entry": PaymentMapping.to_erp,
    }

    mapper = mapping_map.get(external_doctype)
    if mapper:
        return mapper(payload)
    return payload
```

### 3. Add Dead-Letter Queue (DLQ) Routing

**File:** Modify `services/erp_adapter/src/crepro_erp_adapter/push.py`

Update `process_event` to route failures to DLQ:

```python
async def route_to_dlq(
    tenant_id: str,
    event: EventEnvelope,
    reason: str,
) -> None:
    """Route a failed event to the dead-letter queue for manual remediation."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Publish to dead_letter_events topic via Dapr
            await client.post(
                "http://localhost:3500/v1.0/publish/pubsub/dead_letter_events",
                json={
                    "original_event_id": str(event.event_id),
                    "reason": reason,
                    "event": event.model_dump(),
                    "routed_at": datetime.utcnow().isoformat(),
                },
            )
            logger.info(f"Routed to DLQ: {event.event_id} ({reason})")
    except Exception as exc:
        logger.error(f"Failed to route to DLQ: {exc}")

# In process_event(), after max retries:
else:
    # All retries exhausted
    payload_hash = hashlib.sha256(str(context.payload).encode()).hexdigest()
    entry = AdapterLedgerEntry(
        tenant_id=context.tenant_id,
        platform_entity_id=context.platform_entity_id,
        event_type=adapter_event_type,
        external_doctype=external_doctype,
        payload_hash=payload_hash,
        status=AdapterLedgerStatus.FAILED,
        attempts=max_attempts,
        last_error="Max retries exhausted",
    )
    ledger_entries.create(entry)
    
    # Route to DLQ
    await route_to_dlq(
        context.tenant_id,
        event,
        f"Max retries exhausted for {external_doctype}"
    )
    return False
```

## Testing Strategy

Create `services/erp_adapter/tests/test_retry_day12.py`:

```python
@pytest.mark.asyncio
async def test_retry_with_exponential_backoff():
    """Verify exponential backoff timing (1s, 2s, 4s, 8s, 16s)."""
    # Mock post_to_erp_internal to fail first 4 times, succeed on 5th
    attempt_times = []

    async def mock_post(entity_id, doctype, payload):
        attempt_times.append(datetime.utcnow())
        if len(attempt_times) < 5:
            return False, None
        return True, "SUCCESS-001"

    # Verify backoff timing is correct


@pytest.mark.asyncio
async def test_max_retries_routes_to_dlq():
    """Verify poison message goes to DLQ after 5 attempts."""

    # Mock post_to_erp_internal to always fail
    async def mock_post(entity_id, doctype, payload):
        return False, None

    # Verify route_to_dlq is called
    # Verify ledger entry has attempts=5 and status=FAILED


def test_entity_field_mapping_customer():
    """Customer mapping produces correct ERP fields."""
    domain_customer = {
        "name": "ACME Corp",
        "email": "contact@acme.com",
        "type": "company",
        "platform_id": str(uuid4()),
    }

    erp_customer = CustomerMapping.to_erp(domain_customer)

    assert erp_customer["name"] == "ACME Corp"
    assert erp_customer["customer_type"] == "Company"
    assert erp_customer["custom_platform_id"] == domain_customer["platform_id"]
```

## Checklist

- [ ] Create `mappings.py` with CustomerMapping, InvoiceMapping, PaymentMapping
- [ ] Implement `post_to_erp_with_retry()` with exponential backoff
- [ ] Implement `route_to_dlq()` for poison messages
- [ ] Update `process_event()` to use retry logic
- [ ] Add retry tests (backoff timing, DLQ routing, field mapping)
- [ ] Run full test suite (should have 15+ tests now)
- [ ] Verify no regressions from Day 11
- [ ] Commit with message: "Day 12: Adapter mappings, retry policy, and DLQ"
- [ ] Push to feature/day12-adapter-mappings

## Exit Criteria

✅ All retry attempts use correct exponential backoff  
✅ Poison messages route to DLQ after max retries  
✅ Entity field mappings produce correct ERP format  
✅ All tests passing (including Day 11 tests)  
✅ No regressions in existing functionality  
✅ Code ready for Day 13 (reconciliation job)

## Reference Files

- **Day 11 Core:** `services/erp_adapter/src/crepro_erp_adapter/push.py`
- **Day 11 Tests:** `services/erp_adapter/tests/test_push_day11.py`
- **Architecture:** `DAYS_11-15_AND_FRONTEND_ROADMAP.md` (Day 12 section)
- **Status:** `DAY11_COMPLETION_SUMMARY.txt`

---

**Questions?** See `DAYS_11-15_AND_FRONTEND_ROADMAP.md` for detailed Day 12 specification.
