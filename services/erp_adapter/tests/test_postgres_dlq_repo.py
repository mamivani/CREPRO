"""Tests for the PostgreSQL-backed DLQ repository, using a fake asyncpg pool."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from crepro_erp_adapter.postgres_dlq_repo import DLQEventRecord, PostgresDLQRepo


class FakePool:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = []
        self.fetched = []
        self.closed = False

    async def execute(self, sql, *args):
        self.executed.append((sql, args))

    async def fetch(self, sql, *args):
        self.fetched.append((sql, args))
        return self.rows

    async def close(self):
        self.closed = True


def _repo_with(pool: FakePool) -> PostgresDLQRepo:
    repo = PostgresDLQRepo("postgresql://unused")
    repo.pool = pool
    return repo


@pytest.mark.asyncio
async def test_store_event_inserts_pending_row_idempotently() -> None:
    pool = FakePool()
    repo = _repo_with(pool)
    tenant_id, event_id, entity_id = uuid4(), uuid4(), uuid4()

    await repo.store_event(event_id, tenant_id, entity_id, "Customer", "boom", {"name": "Acme"})

    sql, args = pool.executed[0]
    assert "ON CONFLICT (event_id) DO NOTHING" in sql
    assert "'PENDING'" in sql
    assert args[:5] == (tenant_id, event_id, entity_id, "Customer", "boom")
    assert '"name": "Acme"' in args[5]


@pytest.mark.asyncio
async def test_get_pending_events_maps_rows_to_replay_records() -> None:
    tenant_id, event_id, entity_id = uuid4(), uuid4(), uuid4()
    row = {
        "id": uuid4(),
        "tenant_id": tenant_id,
        "event_id": event_id,
        "platform_entity_id": entity_id,
        "external_doctype": "Customer",
        "reason": "boom",
        "payload": '{"name": "Acme"}',
        "status": "PENDING",
        "retry_count": 1,
        "routed_at": datetime.utcnow(),
        "last_retry_at": None,
    }
    repo = _repo_with(FakePool(rows=[row]))

    events = await repo.get_pending_events(tenant_id, datetime.utcnow() - timedelta(hours=1))

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, DLQEventRecord)
    assert event.original_event_id == event_id
    assert event.entity_id == entity_id
    assert event.original_payload == {"name": "Acme"}
    assert event.retry_count == 1


class FakeRowPool(FakePool):
    def __init__(self, row=None):
        super().__init__()
        self.row = row
        self.fetchrow_calls = []

    async def fetchrow(self, sql, *args):
        self.fetchrow_calls.append((sql, args))
        return self.row


@pytest.mark.asyncio
async def test_get_latest_for_entity_returns_most_recent_event() -> None:
    tenant_id, event_id, entity_id = uuid4(), uuid4(), uuid4()
    row = {
        "id": uuid4(),
        "tenant_id": tenant_id,
        "event_id": event_id,
        "platform_entity_id": entity_id,
        "external_doctype": "Customer",
        "reason": "boom",
        "payload": '{"name": "Acme"}',
        "status": "FAILED",
        "retry_count": 2,
        "routed_at": datetime.utcnow(),
        "last_retry_at": None,
    }
    pool = FakeRowPool(row=row)
    repo = _repo_with(pool)

    event = await repo.get_latest_for_entity(tenant_id, entity_id)

    sql, args = pool.fetchrow_calls[0]
    assert "ORDER BY routed_at DESC" in sql
    assert "LIMIT 1" in sql
    assert args == (tenant_id, entity_id)
    assert isinstance(event, DLQEventRecord)
    assert event.original_event_id == event_id
    assert event.retry_count == 2


@pytest.mark.asyncio
async def test_get_latest_for_entity_returns_none_when_no_row() -> None:
    repo = _repo_with(FakeRowPool(row=None))

    assert await repo.get_latest_for_entity(uuid4(), uuid4()) is None


@pytest.mark.asyncio
async def test_update_sets_whitelisted_columns() -> None:
    pool = FakePool()
    repo = _repo_with(pool)
    record_id = uuid4()

    await repo.update(record_id, status="RECOVERED", retry_count=1)

    sql, args = pool.executed[0]
    assert "status = $2" in sql
    assert "retry_count = $3" in sql
    assert args == (record_id, "RECOVERED", 1)


@pytest.mark.asyncio
async def test_update_rejects_identity_columns() -> None:
    repo = _repo_with(FakePool())

    with pytest.raises(ValueError, match="not updatable"):
        await repo.update(uuid4(), payload={})


@pytest.mark.asyncio
async def test_shutdown_closes_pool() -> None:
    pool = FakePool()
    repo = _repo_with(pool)

    await repo.shutdown()

    assert pool.closed is True
    assert repo.pool is None
