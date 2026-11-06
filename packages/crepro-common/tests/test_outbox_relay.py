"""Tests for the outbox relay: the background task that delivers PENDING
outbox entries to Dapr pub/sub (closing the gap left by the outbox pattern's
atomic-write-only guarantee)."""

import asyncio
from uuid import uuid4

import httpx
import pytest
from crepro_common.models import OutboxEntry, OutboxEntryStatus
from crepro_common.outbox import create_outbox_entry
from crepro_common.outbox_relay import relay_pending_outbox_entries, run_outbox_relay_forever
from crepro_common.repository import InMemoryRepository


def _seeded_outbox(entry: OutboxEntry) -> InMemoryRepository[OutboxEntry]:
    outbox: InMemoryRepository[OutboxEntry] = InMemoryRepository()
    outbox.create(entry)
    return outbox


@pytest.mark.asyncio
async def test_relay_marks_entry_published_on_success() -> None:
    entry = create_outbox_entry(
        tenant_id=uuid4(), event_type="PropertyCreated", source="property", payload={"name": "A"}
    )
    outbox = _seeded_outbox(entry)
    requests_seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests_seen.append(request)
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    relayed = await relay_pending_outbox_entries(outbox, client=client)
    await client.aclose()

    assert relayed == 1
    assert len(requests_seen) == 1
    assert "/v1.0/publish/pubsub/erp-events" in str(requests_seen[0].url)
    refreshed = outbox.get(entry.tenant_id, entry.id)
    assert refreshed.status == OutboxEntryStatus.PUBLISHED
    assert refreshed.published_at is not None


@pytest.mark.asyncio
async def test_relay_marks_entry_failed_when_publish_errors() -> None:
    entry = create_outbox_entry(
        tenant_id=uuid4(), event_type="PropertyCreated", source="property", payload={"name": "A"}
    )
    outbox = _seeded_outbox(entry)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    relayed = await relay_pending_outbox_entries(outbox, client=client)
    await client.aclose()

    assert relayed == 0
    refreshed = outbox.get(entry.tenant_id, entry.id)
    assert refreshed.status == OutboxEntryStatus.FAILED
    assert refreshed.retry_count == 1
    assert refreshed.last_error


@pytest.mark.asyncio
async def test_relay_is_a_no_op_with_nothing_pending() -> None:
    outbox: InMemoryRepository[OutboxEntry] = InMemoryRepository()

    assert await relay_pending_outbox_entries(outbox) == 0


@pytest.mark.asyncio
async def test_relay_skips_already_published_entries() -> None:
    entry = create_outbox_entry(
        tenant_id=uuid4(), event_type="PropertyCreated", source="property", payload={}
    )
    entry.status = OutboxEntryStatus.PUBLISHED
    outbox = _seeded_outbox(entry)
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    relayed = await relay_pending_outbox_entries(outbox, client=client)
    await client.aclose()

    assert relayed == 0
    assert calls == []


@pytest.mark.asyncio
async def test_run_outbox_relay_forever_polls_until_cancelled(monkeypatch) -> None:
    outbox: InMemoryRepository[OutboxEntry] = InMemoryRepository()
    tick_count = 0

    async def fake_relay(*args, **kwargs):
        nonlocal tick_count
        tick_count += 1
        return 0

    monkeypatch.setattr("crepro_common.outbox_relay.relay_pending_outbox_entries", fake_relay)

    task = asyncio.create_task(run_outbox_relay_forever(outbox, interval_seconds=0.01))
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert tick_count >= 1
