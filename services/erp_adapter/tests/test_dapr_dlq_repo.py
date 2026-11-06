"""Tests for DaprDLQRepo: the Dapr state-store-backed DLQ repository that
route_to_dlq (push.py) now actually uses to persist dead-lettered events for
Day 13 reconciliation's dlq_replay to pick up, instead of publishing to an
orphaned pub/sub topic nothing subscribed to.

Uses a minimal fake Dapr client (the real class is duck-typed against `Any`
and never imports the `dapr` SDK itself), so these tests exercise the actual
state-store read/write/query logic without needing Dapr installed.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from crepro_erp_adapter.dapr_dlq_repo import DaprDLQRepo


@dataclass
class _StateResponse:
    data: str


class _FakeDaprClient:
    """In-memory stand-in for dapr.clients.DaprClient's state API."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.deleted: list[str] = []

    def save_state(self, store_name: str, key: str, value: str) -> None:
        self.store[key] = value

    def get_state(self, store_name: str, key: str) -> _StateResponse | None:
        if key not in self.store:
            return None
        return _StateResponse(data=self.store[key])

    def query_state(self, store_name: str, pattern: str) -> dict:
        prefix = pattern.rstrip("*")
        return {"results": [{"value": v} for k, v in self.store.items() if k.startswith(prefix)]}

    def delete_state(self, store_name: str, key: str) -> None:
        self.deleted.append(key)
        self.store.pop(key, None)


@pytest.fixture
def repo() -> tuple[DaprDLQRepo, _FakeDaprClient]:
    client = _FakeDaprClient()
    return DaprDLQRepo(client, state_store="dlq-store"), client


@pytest.mark.asyncio
async def test_store_event_persists_as_pending(repo) -> None:
    dlq_repo, client = repo
    event_id, tenant_id, entity_id = uuid4(), uuid4(), uuid4()

    await dlq_repo.store_event(event_id, tenant_id, entity_id, "Customer", "boom", {"name": "Acme"})

    stored = json.loads(client.store[f"dlq:{tenant_id}:{event_id}"])
    assert stored["status"] == "PENDING"
    assert stored["reason"] == "boom"
    assert stored["payload"] == {"name": "Acme"}


@pytest.mark.asyncio
async def test_store_event_raises_on_state_store_error(repo) -> None:
    dlq_repo, client = repo
    client.save_state = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("unreachable"))

    with pytest.raises(RuntimeError):
        await dlq_repo.store_event(uuid4(), uuid4(), uuid4(), "Customer", "boom", {})


@pytest.mark.asyncio
async def test_get_pending_events_returns_recent_pending_events(repo) -> None:
    dlq_repo, client = repo
    tenant_id, event_id = uuid4(), uuid4()
    await dlq_repo.store_event(event_id, tenant_id, uuid4(), "Customer", "boom", {})

    events = await dlq_repo.get_pending_events(tenant_id, hours=24)

    assert len(events) == 1
    assert events[0]["event_id"] == str(event_id)


@pytest.mark.asyncio
async def test_get_pending_events_excludes_events_older_than_window(repo) -> None:
    dlq_repo, client = repo
    tenant_id, event_id = uuid4(), uuid4()
    stale = {
        "event_id": str(event_id),
        "tenant_id": str(tenant_id),
        "status": "PENDING",
        "routed_at": (datetime.now(UTC) - timedelta(hours=48)).replace(tzinfo=None).isoformat(),
    }
    client.store[f"dlq:{tenant_id}:{event_id}"] = json.dumps(stale)

    events = await dlq_repo.get_pending_events(tenant_id, hours=24)

    assert events == []


@pytest.mark.asyncio
async def test_get_pending_events_raises_on_query_error(repo) -> None:
    dlq_repo, client = repo

    def boom(*args, **kwargs):
        raise RuntimeError("state store unreachable")

    client.query_state = boom
    with pytest.raises(RuntimeError):
        await dlq_repo.get_pending_events(uuid4())


@pytest.mark.asyncio
async def test_update_event_applies_fields(repo) -> None:
    dlq_repo, client = repo
    tenant_id, event_id = uuid4(), uuid4()
    await dlq_repo.store_event(event_id, tenant_id, uuid4(), "Customer", "boom", {})

    await dlq_repo.update_event(event_id, tenant_id, {"status": "RECOVERED", "retry_count": 1})

    stored = json.loads(client.store[f"dlq:{tenant_id}:{event_id}"])
    assert stored["status"] == "RECOVERED"
    assert stored["retry_count"] == 1


@pytest.mark.asyncio
async def test_update_event_on_missing_event_is_a_no_op(repo) -> None:
    dlq_repo, client = repo

    await dlq_repo.update_event(uuid4(), uuid4(), {"status": "RECOVERED"})  # must not raise


@pytest.mark.asyncio
async def test_mark_recovered_sets_status(repo) -> None:
    dlq_repo, client = repo
    tenant_id, event_id = uuid4(), uuid4()
    await dlq_repo.store_event(event_id, tenant_id, uuid4(), "Customer", "boom", {})

    await dlq_repo.mark_recovered(event_id, tenant_id)

    assert json.loads(client.store[f"dlq:{tenant_id}:{event_id}"])["status"] == "RECOVERED"


@pytest.mark.asyncio
async def test_mark_manual_review_sets_status(repo) -> None:
    dlq_repo, client = repo
    tenant_id, event_id = uuid4(), uuid4()
    await dlq_repo.store_event(event_id, tenant_id, uuid4(), "Customer", "boom", {})

    await dlq_repo.mark_manual_review(event_id, tenant_id)

    assert json.loads(client.store[f"dlq:{tenant_id}:{event_id}"])["status"] == "MANUAL_REVIEW_REQUIRED"


@pytest.mark.asyncio
async def test_increment_retry_count_increments_and_persists(repo) -> None:
    dlq_repo, client = repo
    tenant_id, event_id = uuid4(), uuid4()
    await dlq_repo.store_event(event_id, tenant_id, uuid4(), "Customer", "boom", {})

    first = await dlq_repo.increment_retry_count(event_id, tenant_id)
    second = await dlq_repo.increment_retry_count(event_id, tenant_id)

    assert (first, second) == (1, 2)


@pytest.mark.asyncio
async def test_increment_retry_count_on_missing_event_returns_zero(repo) -> None:
    dlq_repo, client = repo

    assert await dlq_repo.increment_retry_count(uuid4(), uuid4()) == 0


@pytest.mark.asyncio
async def test_delete_event_removes_from_store(repo) -> None:
    dlq_repo, client = repo
    tenant_id, event_id = uuid4(), uuid4()
    await dlq_repo.store_event(event_id, tenant_id, uuid4(), "Customer", "boom", {})

    await dlq_repo.delete_event(event_id, tenant_id)

    assert f"dlq:{tenant_id}:{event_id}" not in client.store


@pytest.mark.asyncio
async def test_delete_event_raises_on_state_store_error(repo) -> None:
    dlq_repo, client = repo
    client.delete_state = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("unreachable"))

    with pytest.raises(RuntimeError):
        await dlq_repo.delete_event(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_update_event_raises_on_state_store_error(repo) -> None:
    dlq_repo, client = repo
    tenant_id, event_id = uuid4(), uuid4()
    await dlq_repo.store_event(event_id, tenant_id, uuid4(), "Customer", "boom", {})
    client.save_state = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("unreachable"))

    with pytest.raises(RuntimeError):
        await dlq_repo.update_event(event_id, tenant_id, {"status": "RECOVERED"})


@pytest.mark.asyncio
async def test_increment_retry_count_raises_on_state_store_error(repo) -> None:
    dlq_repo, client = repo
    tenant_id, event_id = uuid4(), uuid4()
    await dlq_repo.store_event(event_id, tenant_id, uuid4(), "Customer", "boom", {})
    client.save_state = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("unreachable"))

    with pytest.raises(RuntimeError):
        await dlq_repo.increment_retry_count(event_id, tenant_id)
