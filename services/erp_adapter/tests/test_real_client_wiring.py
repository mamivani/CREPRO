"""Tests for push.py's lazy resolution of the real ERP/DLQ clients.

Closes the Phase 1 gap where the Dapr push handler ignored the ERPClient and
DLQ repo built that phase entirely, and always talked to a hardcoded,
nonexistent `http://localhost:8011` / orphaned pub/sub topic instead.
"""

from uuid import uuid4

import httpx
import pytest
import respx
from crepro_erp_adapter import push


@pytest.fixture(autouse=True)
def reset_client_cache():
    """These are lazily-resolved, cached module globals: reset between tests."""
    push._erp_client = None
    push._dlq_repo = None
    push._dlq_repo_resolved = False
    yield
    push._erp_client = None
    push._dlq_repo = None
    push._dlq_repo_resolved = False


def test_resolve_erp_client_returns_none_without_erp_base_url(monkeypatch) -> None:
    monkeypatch.delenv("ERP_BASE_URL", raising=False)

    assert push._resolve_erp_client() is None


def test_resolve_erp_client_builds_and_caches_client(monkeypatch) -> None:
    monkeypatch.setenv("ERP_BASE_URL", "https://erp.example.com")
    monkeypatch.setenv("ERP_USERNAME", "Administrator")
    monkeypatch.setenv("ERP_PASSWORD", "secret")

    client = push._resolve_erp_client()

    assert client is not None
    assert client.base_url == "https://erp.example.com"
    assert push._resolve_erp_client() is client  # cached, not rebuilt


@pytest.mark.asyncio
async def test_resolve_dlq_repo_returns_none_without_database_url(monkeypatch) -> None:
    monkeypatch.delenv("CREPRO_DATABASE_URL", raising=False)

    assert await push._resolve_dlq_repo() is None


@pytest.mark.asyncio
async def test_resolve_dlq_repo_builds_and_caches_repo(monkeypatch) -> None:
    from crepro_erp_adapter.postgres_dlq_repo import PostgresDLQRepo

    monkeypatch.setenv("CREPRO_DATABASE_URL", "postgresql://user:pass@localhost/db")

    async def fake_initialize(self):
        pass

    monkeypatch.setattr(PostgresDLQRepo, "initialize", fake_initialize)

    repo = await push._resolve_dlq_repo()

    assert isinstance(repo, PostgresDLQRepo)
    # Resolution only happens once; a second call reuses the cached repo.
    assert await push._resolve_dlq_repo() is repo


@pytest.mark.asyncio
async def test_resolve_dlq_repo_degrades_when_pool_init_fails(monkeypatch) -> None:
    """An unreachable database must be logged and return None, never raise."""
    from crepro_erp_adapter.postgres_dlq_repo import PostgresDLQRepo

    monkeypatch.setenv("CREPRO_DATABASE_URL", "postgresql://user:pass@localhost/db")

    async def boom(self):
        raise OSError("connection refused")

    monkeypatch.setattr(PostgresDLQRepo, "initialize", boom)

    assert await push._resolve_dlq_repo() is None
    # Resolution only happens once; a second call reuses the cached None.
    assert await push._resolve_dlq_repo() is None


@pytest.mark.asyncio
async def test_check_idempotency_internal_queries_real_erp(monkeypatch) -> None:
    monkeypatch.setenv("ERP_BASE_URL", "https://erp.example.com")
    entity_id = uuid4()

    with respx.mock:
        respx.get("https://erp.example.com/api/resource/Customer").mock(
            return_value=httpx.Response(200, json={"data": [{"name": "CUST-001"}]})
        )
        is_posted, name = await push.check_idempotency_internal(entity_id, "Customer")

    assert is_posted is True
    assert name == "CUST-001"


@pytest.mark.asyncio
async def test_check_idempotency_internal_without_erp_configured(monkeypatch) -> None:
    monkeypatch.delenv("ERP_BASE_URL", raising=False)

    is_posted, name = await push.check_idempotency_internal(uuid4(), "Customer")

    assert (is_posted, name) == (False, None)


@pytest.mark.asyncio
async def test_check_idempotency_internal_reports_not_posted_on_erp_error(monkeypatch) -> None:
    """A configured but unreachable/erroring ERP must not be mistaken for 'already posted'."""
    monkeypatch.setenv("ERP_BASE_URL", "https://erp.example.com")

    with respx.mock:
        respx.get("https://erp.example.com/api/resource/Customer").mock(return_value=httpx.Response(500))
        is_posted, name = await push.check_idempotency_internal(uuid4(), "Customer")

    assert (is_posted, name) == (False, None)


@pytest.mark.asyncio
async def test_post_to_erp_internal_creates_real_erp_record(monkeypatch) -> None:
    monkeypatch.setenv("ERP_BASE_URL", "https://erp.example.com")
    entity_id = uuid4()

    with respx.mock:
        respx.post("https://erp.example.com/api/resource/Customer").mock(
            return_value=httpx.Response(200, json={"data": {"name": "CUST-002"}})
        )
        success, name = await push.post_to_erp_internal(entity_id, "Customer", {"name": "Acme"})

    assert success is True
    assert name == "CUST-002"


@pytest.mark.asyncio
async def test_post_to_erp_internal_without_erp_configured(monkeypatch) -> None:
    monkeypatch.delenv("ERP_BASE_URL", raising=False)

    success, name = await push.post_to_erp_internal(uuid4(), "Customer", {"name": "Acme"})

    assert (success, name) == (False, None)


@pytest.mark.asyncio
async def test_post_to_erp_internal_fails_cleanly_on_erp_error(monkeypatch) -> None:
    monkeypatch.setenv("ERP_BASE_URL", "https://erp.example.com")

    with respx.mock:
        respx.post("https://erp.example.com/api/resource/Customer").mock(return_value=httpx.Response(503))
        success, name = await push.post_to_erp_internal(uuid4(), "Customer", {"name": "Acme"})

    assert (success, name) == (False, None)


@pytest.mark.asyncio
async def test_route_to_dlq_is_a_safe_no_op_without_database_url(monkeypatch) -> None:
    monkeypatch.delenv("CREPRO_DATABASE_URL", raising=False)

    # Must not raise even though nothing is configured to persist the DLQ event
    # (the failure is already recorded in the ledger by the caller).
    await push.route_to_dlq(str(uuid4()), uuid4(), uuid4(), "Customer", "boom", {"name": "Acme"})
