"""Tests for main.py: the reconciliation job's entry point and client selection.

Covers _initialize_clients' mock/production branching (incl. the cross-package
import from crepro_erp_adapter, which only works now that crepro-erp-adapter is
an installed dependency of this service) and run_reconciliation_job's mode
dispatch, invalid-input handling, and cleanup.
"""

from uuid import uuid4

import pytest
from crepro_erp_reconciliation.main import (
    MockAdapterClient,
    MockDLQRepo,
    MockERPClient,
    MockLedgerRepo,
    _initialize_clients,
    run_reconciliation_job,
)


@pytest.mark.asyncio
async def test_initialize_clients_uses_mocks_by_default(monkeypatch) -> None:
    for var in ("ERP_BASE_URL", "DATABASE_URL", "ADAPTER_SERVICE_URL"):
        monkeypatch.delenv(var, raising=False)

    erp_client, ledger_repo, dlq_repo, adapter_client = await _initialize_clients()

    assert isinstance(erp_client, MockERPClient)
    assert isinstance(ledger_repo, MockLedgerRepo)
    assert isinstance(dlq_repo, MockDLQRepo)
    assert isinstance(adapter_client, MockAdapterClient)


@pytest.mark.asyncio
async def test_initialize_clients_uses_mocks_when_only_some_vars_set(monkeypatch) -> None:
    monkeypatch.setenv("ERP_BASE_URL", "https://erp.example.com")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ADAPTER_SERVICE_URL", raising=False)

    erp_client, *_ = await _initialize_clients()

    assert isinstance(erp_client, MockERPClient)


@pytest.mark.asyncio
async def test_initialize_clients_builds_real_clients_when_fully_configured(monkeypatch) -> None:
    from crepro_erp_adapter.adapter_service_client import AdapterServiceClient
    from crepro_erp_adapter.erp_client import ERPClient
    from crepro_erp_adapter.postgres_dlq_repo import PostgresDLQRepo
    from crepro_erp_adapter.postgres_ledger_repo import PostgresLedgerRepo

    monkeypatch.setenv("ERP_BASE_URL", "https://erp.example.com")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@host/db")
    monkeypatch.setenv("ADAPTER_SERVICE_URL", "http://erp-adapter.internal")

    async def fake_initialize(self):
        pass

    monkeypatch.setattr(PostgresLedgerRepo, "initialize", fake_initialize)
    monkeypatch.setattr(PostgresDLQRepo, "initialize", fake_initialize)

    erp_client, ledger_repo, dlq_repo, adapter_client = await _initialize_clients()

    assert isinstance(erp_client, ERPClient)
    assert erp_client.base_url == "https://erp.example.com"
    assert isinstance(ledger_repo, PostgresLedgerRepo)
    assert isinstance(adapter_client, AdapterServiceClient)
    assert isinstance(dlq_repo, PostgresDLQRepo)


@pytest.mark.asyncio
async def test_run_reconciliation_job_invalid_tenant_id_returns_without_raising(monkeypatch) -> None:
    monkeypatch.setenv("TENANT_ID", "not-a-uuid")

    await run_reconciliation_job()  # must not raise


@pytest.mark.asyncio
async def test_run_reconciliation_job_runs_incremental_and_dlq_replay_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ERP_BASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ADAPTER_SERVICE_URL", raising=False)
    monkeypatch.delenv("RECONCILIATION_MODE", raising=False)
    monkeypatch.setenv("TENANT_ID", str(uuid4()))

    await run_reconciliation_job()  # mocks return empty results; must complete cleanly


@pytest.mark.asyncio
async def test_run_reconciliation_job_full_mode(monkeypatch) -> None:
    monkeypatch.setenv("RECONCILIATION_MODE", "full")
    monkeypatch.setenv("TENANT_ID", str(uuid4()))

    await run_reconciliation_job()


@pytest.mark.asyncio
async def test_run_reconciliation_job_unknown_mode_logs_and_completes(monkeypatch) -> None:
    monkeypatch.setenv("RECONCILIATION_MODE", "BOGUS")
    monkeypatch.setenv("TENANT_ID", str(uuid4()))

    await run_reconciliation_job()  # must not raise, just logs an error


@pytest.mark.asyncio
async def test_run_reconciliation_job_shuts_down_ledger_repo_with_shutdown_method(monkeypatch) -> None:
    """Covers the `if hasattr(ledger_repo, "shutdown")` cleanup path, which MockLedgerRepo
    doesn't have but PostgresLedgerRepo does."""
    from crepro_erp_adapter.postgres_dlq_repo import PostgresDLQRepo
    from crepro_erp_adapter.postgres_ledger_repo import PostgresLedgerRepo

    monkeypatch.setenv("ERP_BASE_URL", "https://erp.example.com")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@host/db")
    monkeypatch.setenv("ADAPTER_SERVICE_URL", "http://erp-adapter.internal")
    monkeypatch.setenv("RECONCILIATION_MODE", "INCREMENTAL")
    monkeypatch.setenv("TENANT_ID", str(uuid4()))

    shutdown_calls = []

    async def fake_initialize(self):
        pass

    async def fake_shutdown(self):
        shutdown_calls.append(type(self).__name__)

    async def fake_scan(*args, **kwargs):
        return "scan-report"

    async def fake_replay(*args, **kwargs):
        return "replay-report"

    monkeypatch.setattr(PostgresLedgerRepo, "initialize", fake_initialize)
    monkeypatch.setattr(PostgresLedgerRepo, "shutdown", fake_shutdown)
    monkeypatch.setattr(PostgresDLQRepo, "initialize", fake_initialize)
    monkeypatch.setattr(PostgresDLQRepo, "shutdown", fake_shutdown)
    monkeypatch.setattr("crepro_erp_reconciliation.main.run_incremental_scan", fake_scan)
    monkeypatch.setattr("crepro_erp_reconciliation.main.replay_dlq_events", fake_replay)

    await run_reconciliation_job()

    assert sorted(shutdown_calls) == ["PostgresDLQRepo", "PostgresLedgerRepo"]


@pytest.mark.asyncio
async def test_run_reconciliation_job_reraises_scan_failures_after_cleanup(monkeypatch) -> None:
    monkeypatch.setenv("TENANT_ID", str(uuid4()))

    async def boom(*args, **kwargs):
        raise RuntimeError("scan failed")

    monkeypatch.setattr("crepro_erp_reconciliation.main.run_incremental_scan", boom)

    with pytest.raises(RuntimeError, match="scan failed"):
        await run_reconciliation_job()


@pytest.mark.asyncio
async def test_run_reconciliation_job_runs_dlq_replay_in_production(monkeypatch) -> None:
    """Production wiring builds a PostgresDLQRepo, so replay runs in the job."""
    from crepro_erp_adapter.postgres_dlq_repo import PostgresDLQRepo
    from crepro_erp_adapter.postgres_ledger_repo import PostgresLedgerRepo

    monkeypatch.setenv("ERP_BASE_URL", "https://erp.example.com")
    monkeypatch.setenv("DATABASE_URL", "******host/db")
    monkeypatch.setenv("ADAPTER_SERVICE_URL", "http://erp-adapter.internal")
    monkeypatch.setenv("RECONCILIATION_MODE", "INCREMENTAL")
    monkeypatch.setenv("TENANT_ID", str(uuid4()))

    replay_calls = []

    async def fake_initialize(self):
        pass

    async def fake_scan(*args, **kwargs):
        return "scan-report"

    async def fake_replay(*args, **kwargs):
        replay_calls.append(True)
        return "replay-report"

    monkeypatch.setattr(PostgresLedgerRepo, "initialize", fake_initialize)
    monkeypatch.setattr(PostgresDLQRepo, "initialize", fake_initialize)
    monkeypatch.setattr("crepro_erp_reconciliation.main.run_incremental_scan", fake_scan)
    monkeypatch.setattr("crepro_erp_reconciliation.main.replay_dlq_events", fake_replay)

    await run_reconciliation_job()

    assert replay_calls == [True]


@pytest.mark.asyncio
async def test_mock_clients_implement_expected_interface() -> None:
    """The fallback Mock* classes are only ever exercised in the tests above via
    empty-collection paths (no ERP/ledger/DLQ records to iterate over), so their
    individual method bodies need direct coverage too."""
    tenant_id = uuid4()
    entity_id = uuid4()

    erp_client = MockERPClient()
    assert await erp_client.get_record(tenant_id, "Customer", "CUST-1") is None

    ledger_repo = MockLedgerRepo()
    assert ledger_repo.get_by_platform_id(tenant_id, entity_id) is None
    assert (
        ledger_repo.create(
            tenant_id=tenant_id,
            entity_id=entity_id,
            status="POSTED",
            erp_docid="CUST-1",
            external_doctype="Customer",
        )
        is None
    )
    assert ledger_repo.update(uuid4()) is None

    dlq_repo = MockDLQRepo()
    assert await dlq_repo.update(uuid4()) is None

    adapter_client = MockAdapterClient()
    assert await adapter_client.repost_entity(tenant_id, entity_id, "Customer", {}) == (False, None)


def test_main_invokes_asyncio_run_with_the_reconciliation_job(monkeypatch) -> None:
    import crepro_erp_reconciliation.main as module

    calls = []

    def fake_run(coro):
        calls.append(coro)
        coro.close()  # avoid an "coroutine was never awaited" warning

    monkeypatch.setattr(module.asyncio, "run", fake_run)

    module.main()

    assert len(calls) == 1
