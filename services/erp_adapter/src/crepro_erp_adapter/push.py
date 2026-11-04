"""ERP Adapter push path: subscribes to domain events and posts to external ERP.

This is a Dapr pub/sub subscriber that:
1. Receives events published by domain services (via the outbox relay on erp-events topic)
2. Checks idempotency via platform_id custom field on the external ERP
3. Posts to the external ERP if not already posted
4. Records ledger entries for audit and retry purposes

Session key: tenantId:entityId (unique per tenant and entity).
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import httpx
from crepro_common import EventEnvelope
from crepro_erp_adapter.mappings import apply_entity_mapping
from crepro_erp_adapter.models import AdapterEventType, AdapterLedgerEntry, AdapterLedgerStatus
from crepro_erp_adapter.repository import ledger_entries

logger = logging.getLogger(__name__)

# Exponential backoff times (seconds) for retry attempts
RETRY_BACKOFF_SECONDS = [1, 2, 4, 8, 16]
MAX_RETRY_ATTEMPTS = 5


@dataclass
class ErpPushContext:
    """Context for posting to external ERP."""

    tenant_id: str
    event_id: UUID
    event_type: str
    platform_entity_id: UUID
    payload: dict


async def check_idempotency_internal(
    entity_id: UUID,
    external_doctype: str,
) -> tuple[bool, str | None]:
    """
    Check if an entity has already been posted to external ERP via platform_id custom field.

    Returns (is_posted, external_name) where external_name is set if already posted.
    
    For testing, this is mocked. In production, it queries the external ERP.
    """
    try:
        # In production, this would call the external ERP API
        # For now, assume implementation will be provided at integration time
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                "http://localhost:8011/api/resource/{0}".format(external_doctype),
                params={
                    "fields": '["name"]',
                    "filters": '[["custom_platform_id", "=", "{0}"]]'.format(entity_id),
                },
            )
            response.raise_for_status()
            data = response.json()
            if data.get("data") and len(data["data"]) > 0:
                return True, data["data"][0].get("name")
            return False, None
    except Exception as exc:
        logger.error(
            f"Idempotency check failed for {external_doctype} {entity_id}: {exc}",
        )
        return False, None


async def post_to_erp_internal(
    entity_id: UUID,
    external_doctype: str,
    payload: dict,
) -> tuple[bool, str | None]:
    """
    Post entity to external ERP, adding platform_id for idempotency.

    Returns (success, external_name) where external_name is returned if successful.
    
    For testing, this is mocked. In production, it calls the external ERP.
    """
    try:
        # Add platform_id to payload for idempotency
        payload_with_platform_id = {
            **payload,
            "custom_platform_id": str(entity_id),
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "http://localhost:8011/api/resource/{0}".format(external_doctype),
                json=payload_with_platform_id,
            )
            response.raise_for_status()
            data = response.json()
            external_name = data.get("data", {}).get("name")
            logger.info(
                f"Posted {external_doctype}: platform_id={entity_id}, external_name={external_name}",
            )
            return True, external_name
    except Exception as exc:
        logger.error(
            f"Failed to post {external_doctype} {entity_id}: {exc}",
        )
        return False, None


async def check_idempotency(
    tenant_id: str,
    entity_id: UUID,
    erp_client: httpx.AsyncClient,
    external_doctype: str,
) -> str | None:
    """
    Check if an entity has already been posted to external ERP via platform_id custom field.

    Returns the external name (e.g., "INV-001234") if already posted, None otherwise.
    """
    is_posted, external_name = await check_idempotency_internal(entity_id, external_doctype)
    return external_name if is_posted else None


async def post_to_erp(
    tenant_id: str,
    entity_id: UUID,
    erp_client: httpx.AsyncClient,
    external_doctype: str,
    payload: dict,
) -> str | None:
    """
    Post entity to external ERP, adding platform_id for idempotency.

    Returns the external name (e.g., "INV-001234") if successful, None on failure.
    """
    success, external_name = await post_to_erp_internal(entity_id, external_doctype, payload)
    return external_name if success else None


async def post_to_erp_with_retry(
    tenant_id: str,
    entity_id: UUID,
    erp_client: httpx.AsyncClient,
    external_doctype: str,
    payload: dict,
    event_id: UUID,
    adapter_event_type: AdapterEventType,
) -> tuple[bool, str | None]:
    """
    Post to ERP with exponential backoff retry.

    Attempts to post up to MAX_RETRY_ATTEMPTS times with exponential backoff.
    On each failure, updates the ledger with attempt count and error.
    After max attempts exhausted, routes to DLQ.

    Returns (success, external_name) tuple.
    On success: (True, external_name)
    On max retries: (False, None) after routing to DLQ
    """
    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        try:
            # Apply entity-specific field mapping
            mapped_payload = apply_entity_mapping(external_doctype, payload)

            # Try to post
            success, external_name = await post_to_erp_internal(
                entity_id, external_doctype, mapped_payload
            )

            if success:
                logger.info(
                    f"Posted successfully on attempt {attempt}: "
                    f"{external_doctype} {entity_id} -> {external_name}"
                )
                return True, external_name

            # Post failed, will retry
            logger.warning(
                f"Post failed on attempt {attempt}/{MAX_RETRY_ATTEMPTS}: "
                f"{external_doctype} {entity_id}"
            )

            # Update ledger with attempt count
            _update_ledger_attempt(
                tenant_id, entity_id, adapter_event_type, external_doctype,
                attempt, f"Attempt {attempt}/{MAX_RETRY_ATTEMPTS} failed"
            )

            if attempt < MAX_RETRY_ATTEMPTS:
                # Wait before retry (exponential backoff)
                backoff_seconds = RETRY_BACKOFF_SECONDS[attempt - 1]
                logger.info(f"Retrying in {backoff_seconds}s...")
                await asyncio.sleep(backoff_seconds)

        except Exception as exc:
            logger.error(f"Exception on attempt {attempt}: {exc}")
            _update_ledger_attempt(
                tenant_id, entity_id, adapter_event_type, external_doctype,
                attempt, f"Attempt {attempt} failed: {str(exc)}"
            )

            if attempt < MAX_RETRY_ATTEMPTS:
                backoff_seconds = RETRY_BACKOFF_SECONDS[attempt - 1]
                await asyncio.sleep(backoff_seconds)

    # All retries exhausted - mark as FAILED and route to DLQ
    logger.error(
        f"Max retries ({MAX_RETRY_ATTEMPTS}) exhausted for "
        f"{external_doctype} {entity_id}"
    )

    # Final update to ledger
    payload_hash = hashlib.sha256(str(payload).encode()).hexdigest()
    entry = AdapterLedgerEntry(
        tenant_id=tenant_id,
        platform_entity_id=entity_id,
        event_type=adapter_event_type,
        external_doctype=external_doctype,
        payload_hash=payload_hash,
        status=AdapterLedgerStatus.FAILED,
        attempts=MAX_RETRY_ATTEMPTS,
        last_error="Max retries exhausted",
    )
    ledger_entries.create(entry)

    # Route to DLQ
    await route_to_dlq(
        tenant_id, event_id, entity_id, external_doctype,
        f"Max retries ({MAX_RETRY_ATTEMPTS}) exhausted"
    )

    return False, None


def _update_ledger_attempt(
    tenant_id: str,
    entity_id: UUID,
    adapter_event_type: AdapterEventType,
    external_doctype: str,
    attempt: int,
    error_message: str,
) -> None:
    """Update ledger entry with retry attempt information."""
    payload_hash = ""  # Not used for retry updates, already in original entry
    entry = AdapterLedgerEntry(
        tenant_id=tenant_id,
        platform_entity_id=entity_id,
        event_type=adapter_event_type,
        external_doctype=external_doctype,
        payload_hash=payload_hash,
        status=AdapterLedgerStatus.FAILED,
        attempts=attempt,
        last_error=error_message,
    )
    ledger_entries.create(entry)


async def route_to_dlq(
    tenant_id: str,
    event_id: UUID,
    entity_id: UUID,
    external_doctype: str,
    reason: str,
) -> None:
    """
    Route a failed event to the dead-letter queue for manual remediation.

    The DLQ is a separate Dapr pub/sub topic that can be monitored and
    manually handled when automatic retry is exhausted.
    """
    try:
        async with httpx.AsyncClient(timeout=30) as dlq_client:
            # Publish to dead_letter_events topic via Dapr
            dlq_payload = {
                "original_event_id": str(event_id),
                "entity_id": str(entity_id),
                "external_doctype": external_doctype,
                "reason": reason,
                "routed_at": datetime.utcnow().isoformat(),
                "tenant_id": tenant_id,
            }
            await dlq_client.post(
                "http://localhost:3500/v1.0/publish/pubsub/dead_letter_events",
                json=dlq_payload,
            )
            logger.info(
                f"Routed to DLQ: event_id={event_id}, entity_id={entity_id}, "
                f"reason={reason}"
            )
    except Exception as exc:
        logger.error(f"Failed to route to DLQ: {exc}")


def _map_event_type_to_adapter_type(domain_event_type: str) -> AdapterEventType:
    """Map domain event type to adapter event type."""
    mapping = {
        "CustomerCreated": AdapterEventType.CUSTOMER_UPSERTED,
        "CustomerUpdated": AdapterEventType.CUSTOMER_UPSERTED,
        "VendorCreated": AdapterEventType.VENDOR_UPSERTED,
        "VendorUpdated": AdapterEventType.VENDOR_UPSERTED,
        "InvoiceGenerated": AdapterEventType.INVOICE_GENERATED,
        "PaymentRecorded": AdapterEventType.PAYMENT_POSTED,
        "DepositRecorded": AdapterEventType.DEPOSIT_RECORDED,
        "AdjustmentPosted": AdapterEventType.ADJUSTMENT_POSTED,
    }
    return mapping.get(domain_event_type, AdapterEventType.CUSTOMER_UPSERTED)


async def process_event(
    event: EventEnvelope,
    erp_client: httpx.AsyncClient,
) -> bool:
    """
    Process an event from the outbox relay.

    1. Extract tenant_id from event
    2. Get entity_id from the payload or event context
    3. Determine external_doctype from event_type
    4. Check idempotency via platform_id
    5. Post to external ERP if not already posted
    6. Record ledger entry

    Returns True if successfully posted or already exists, False on failure.
    """
    try:
        # Extract entity_id from payload or use a default
        # For Day 11 MVP, we'll use a derived ID from the payload
        entity_id = event.payload.get("platform_id") or event.event_id

        # Parse event
        context = ErpPushContext(
            tenant_id=str(event.tenant_id),
            event_id=event.event_id,
            event_type=event.event_type,
            platform_entity_id=entity_id if isinstance(entity_id, UUID) else UUID(str(entity_id)),
            payload=event.payload,
        )

        # Determine external doctype from event type
        doctype_map = {
            "PropertyCreated": "Property",
            "CustomerCreated": "Customer",
            "CustomerUpdated": "Customer",
            "VendorCreated": "Supplier",
            "VendorUpdated": "Supplier",
            "InvoiceGenerated": "Sales Invoice",
            "PaymentRecorded": "Payment Entry",
            "DepositRecorded": "Payment Entry",
            "AdjustmentPosted": "Journal Entry",
        }
        external_doctype = doctype_map.get(context.event_type)
        if not external_doctype:
            logger.warning(f"Unknown event type: {context.event_type}")
            return False

        # Map domain event type to adapter event type
        adapter_event_type = _map_event_type_to_adapter_type(context.event_type)

        # Check idempotency
        existing_external_name = await check_idempotency(
            context.tenant_id,
            context.platform_entity_id,
            erp_client,
            external_doctype,
        )

        if existing_external_name:
            logger.info(
                f"Entity already posted (idempotent): "
                f"{external_doctype} {context.platform_entity_id} -> {existing_external_name}",
            )
            # Record in ledger for audit
            payload_hash = hashlib.sha256(str(context.payload).encode()).hexdigest()
            entry = AdapterLedgerEntry(
                tenant_id=context.tenant_id,
                platform_entity_id=context.platform_entity_id,
                event_type=adapter_event_type,
                external_doctype=external_doctype,
                external_name=existing_external_name,
                payload_hash=payload_hash,
                status=AdapterLedgerStatus.POSTED,
            )
            ledger_entries.create(entry)
            return True

        # Post to external ERP with retry logic (Day 12)
        success, external_name = await post_to_erp_with_retry(
            context.tenant_id,
            context.platform_entity_id,
            erp_client,
            external_doctype,
            context.payload,
            context.event_id,
            adapter_event_type,
        )

        if success:
            # Record successful post in ledger
            payload_hash = hashlib.sha256(str(context.payload).encode()).hexdigest()
            entry = AdapterLedgerEntry(
                tenant_id=context.tenant_id,
                platform_entity_id=context.platform_entity_id,
                event_type=adapter_event_type,
                external_doctype=external_doctype,
                external_name=external_name,
                payload_hash=payload_hash,
                status=AdapterLedgerStatus.POSTED,
            )
            ledger_entries.create(entry)
            return True
        else:
            # Failed after all retries (already routed to DLQ)
            return False

    except Exception as exc:
        logger.error(f"Error processing event {event.event_id}: {exc}")
        return False


async def start_subscriber(dapr_http_url: str = "http://localhost:3500") -> None:
    """
    Start the Dapr pub/sub subscriber for erp-events topic.

    This is a long-running task that should be started once on app startup.
    """
    async with httpx.AsyncClient(timeout=30) as dapr_client:
        # Subscribe to erp-events via Dapr
        try:
            await dapr_client.post(
                f"{dapr_http_url}/v1.0/subscribe/pubsub/erp-events",
                json={"url": "http://localhost:8011/subscribe/erp-events"},
            )
            logger.info("Subscribed to erp-events topic via Dapr")
        except Exception as exc:
            logger.error(f"Failed to subscribe: {exc}")


def create_subscriber_handler():
    """Create the FastAPI endpoint handler for Dapr pub/sub push delivery."""

    async def handle_event(event: EventEnvelope) -> dict:
        """Handle an event pushed by Dapr."""
        async with httpx.AsyncClient(timeout=30) as erp_client:
            # TODO: Get ERP credentials from Key Vault
            # For now, assume Basic Auth headers are set via environment
            success = await process_event(event, erp_client)
            return {"success": success}

    return handle_event
