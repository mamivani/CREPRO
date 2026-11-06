"""Background relay that delivers pending outbox entries to Dapr pub/sub.

The outbox pattern (see outbox.py) only covers the atomic write: a domain
mutation and a PENDING OutboxEntry land together. Nothing picks that row back
up on its own. This module is the other half: poll for PENDING entries across
every tenant, publish each as an EventEnvelope to the service's Dapr sidecar,
and mark it PUBLISHED or FAILED based on the result.

At-least-once delivery: an entry whose publish succeeds but crashes before
being marked PUBLISHED is retried on the next tick, so consumers (e.g.
erp_adapter) must tolerate duplicate delivery via their own idempotency key
(platform_id), exactly as the exactly-once design already assumes.
"""

import asyncio
import logging

import httpx

from crepro_common.events import EventEnvelope
from crepro_common.models import OutboxEntry, OutboxEntryStatus
from crepro_common.outbox import mark_failed, mark_published
from crepro_common.repository import InMemoryRepository

logger = logging.getLogger(__name__)


async def relay_pending_outbox_entries(
    outbox: InMemoryRepository[OutboxEntry],
    *,
    topic: str = "erp-events",
    pubsub_name: str = "pubsub",
    dapr_http_port: int = 3500,
    client: httpx.AsyncClient | None = None,
) -> int:
    """Publish every currently PENDING outbox entry once.

    Returns how many entries were successfully relayed. Entries are processed
    oldest-first so delivery order roughly matches creation order.
    """
    pending = sorted(
        (entry for entry in outbox.list_all() if entry.status == OutboxEntryStatus.PENDING),
        key=lambda entry: entry.created_at,
    )
    if not pending:
        return 0

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=10)
    url = f"http://localhost:{dapr_http_port}/v1.0/publish/{pubsub_name}/{topic}"
    relayed = 0
    try:
        for entry in pending:
            envelope = EventEnvelope(
                event_id=entry.event_id,
                event_type=entry.event_type,
                tenant_id=entry.tenant_id,
                source=entry.source,
                schema_version=entry.schema_version,
                payload=entry.payload,
            )
            try:
                response = await client.post(
                    url,
                    content=envelope.model_dump_json(),
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
            except Exception as exc:
                logger.warning("Outbox relay: failed to publish entry %s: %s", entry.id, exc)
                mark_failed(outbox, entry.tenant_id, entry.id, str(exc))
                continue
            mark_published(outbox, entry.tenant_id, entry.id)
            relayed += 1
    finally:
        if owns_client:
            await client.aclose()
    return relayed


async def run_outbox_relay_forever(
    outbox: InMemoryRepository[OutboxEntry],
    *,
    topic: str = "erp-events",
    pubsub_name: str = "pubsub",
    dapr_http_port: int = 3500,
    interval_seconds: float = 2.0,
) -> None:
    """Poll `outbox` every `interval_seconds` until the task is cancelled.

    Intended to be started as an `asyncio.Task` from a service's FastAPI
    lifespan (see crepro_common.app.create_app) and cancelled on shutdown.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            try:
                await relay_pending_outbox_entries(
                    outbox,
                    topic=topic,
                    pubsub_name=pubsub_name,
                    dapr_http_port=dapr_http_port,
                    client=client,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Outbox relay tick failed")
            await asyncio.sleep(interval_seconds)
