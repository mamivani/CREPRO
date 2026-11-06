"""HTTP routes for the ERP adapter.

These expose:
1. The adapter ledger and tenant mapping table for inspection and manual repair
2. A Dapr pub/sub push endpoint for receiving domain events from the outbox relay

The pull (reconciliation job) path described in docs/design/erp-adapter-hybrid.md
is a separate scheduled worker, not an HTTP endpoint, and is out of scope for this scaffold.
"""

import logging
from uuid import UUID

from crepro_common import EventEnvelope, build_crud_router
from crepro_erp_adapter.mappings import apply_entity_mapping
from crepro_erp_adapter.models import AdapterLedgerEntry, TenantErpMapping
from crepro_erp_adapter.push import (
    check_idempotency_internal,
    create_subscriber_handler,
    post_to_erp_internal,
)
from crepro_erp_adapter.repository import ledger_entries, tenant_mappings
from crepro_erp_adapter.schemas import (
    AdapterLedgerEntryCreate,
    AdapterLedgerEntryUpdate,
    TenantErpMappingCreate,
    TenantErpMappingUpdate,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

router.include_router(
    build_crud_router(
        prefix="/api/v1/ledger-entries",
        tags=["ledger-entries"],
        repository=ledger_entries,
        entity_cls=AdapterLedgerEntry,
        create_schema=AdapterLedgerEntryCreate,
        update_schema=AdapterLedgerEntryUpdate,
        not_found_detail="Ledger entry not found",
    )
)

router.include_router(
    build_crud_router(
        prefix="/api/v1/tenant-mappings",
        tags=["tenant-mappings"],
        repository=tenant_mappings,
        entity_cls=TenantErpMapping,
        create_schema=TenantErpMappingCreate,
        update_schema=TenantErpMappingUpdate,
        not_found_detail="Tenant mapping not found",
    )
)


@router.get("/dapr/subscribe", tags=["pub/sub"])
async def dapr_subscriptions() -> list[dict[str, str]]:
    """Programmatic subscription list the Dapr sidecar reads at startup.

    This is the single subscription mechanism for local compose and Azure Container Apps.
    """
    return [{"pubsubname": "pubsub", "topic": "erp-events", "route": "/subscribe/erp-events"}]


# Dapr pub/sub push endpoint
@router.post("/subscribe/erp-events", tags=["pub/sub"])
async def subscribe_erp_events(event: EventEnvelope) -> dict:
    """
    Dapr pub/sub push endpoint for erp-events topic.

    This endpoint is called by Dapr when a new event is published to erp-events.
    The handler checks idempotency and posts to the external ERP if not already posted.
    """
    logger.debug(f"Received event: {event.event_type} from {event.source}")
    handler = create_subscriber_handler()
    result = await handler(event)
    return result


class RepostRequest(BaseModel):
    tenant_id: UUID
    entity_id: UUID
    external_doctype: str
    payload: dict


@router.post("/api/repost", tags=["reconciliation"])
async def repost_entity(request: RepostRequest) -> dict:
    """Repost a dead-lettered entity for the reconciliation DLQ replay.

    Checks idempotency on the ERP first, so a replay of an entity that already
    landed in the ERP returns its existing name instead of creating a duplicate.
    """
    already_posted, existing_name = await check_idempotency_internal(
        request.entity_id, request.external_doctype
    )
    if already_posted:
        return {"external_name": existing_name}

    mapped_payload = apply_entity_mapping(request.external_doctype, request.payload)
    success, external_name = await post_to_erp_internal(
        request.entity_id, request.external_doctype, mapped_payload
    )
    if not success:
        raise HTTPException(status_code=502, detail="ERP post failed")
    return {"external_name": external_name}
