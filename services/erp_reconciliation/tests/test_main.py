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
    from crepro_erp_adapter.erp_client import ERPClient
    from crepro_erp_adapter.postgres_ledger_repo import PostgresLedgerRepo
    from crepro_erp_adapter.adapter_service_client import AdapterServiceClient

    monkeypatch.setenv("ERP_BASE_URL", "https://erp.example.com")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@host/db")
    monkeypatch.setenv("ADAPTER_SERVICE_URL", "http://erp-adapter.internal")
    monkeypatch.delenv("DAPR_STATE_STORE", raising=False)

    async def fake_initialize(self):
        pass

    monkeypatch.setattr(PostgresLedgerRepo, "initialize", fake_initialize)

    erp_client, ledger_repo, dlq_repo, adapter_client = await _initialize_clients()

    assert isinstance(erp_client, ERPClient)
    assert erp_client.base_url == "https://erp.example.com"
    assert isinstance(ledger_repo, PostgresLedgerRepo)
    assert isinstance(adapter_client, AdapterServiceClient)
    # No Dapr sidecar reachable in the test environment: falls back to mock, not a crash.
    assert isinstance(dlq_repo, MockDLQRepo)


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
        shutdown_calls.append(True)

    async def fake_scan(*args, **kwargs):
        return "scan-report"

    async def fake_replay(*args, **kwargs):
        return "replay-report"

    monkeypatch.setattr(PostgresLedgerRepo, "initialize", fake_initialize)
    monkeypatch.setattr(PostgresLedgerRepo, "shutdown", fake_shutdown)
    monkeypatch.setattr("crepro_erp_reconciliation.main.run_incremental_scan", fake_scan)
    monkeypatch.setattr("crepro_erp_reconciliation.main.replay_dlq_events", fake_replay)

    await run_reconciliation_job()

    assert shutdown_calls == [True]


@pytest.mark.asyncio
async def test_run_reconciliation_job_reraises_scan_failures_after_cleanup(monkeypatch) -> None:
    monkeypatch.setenv("TENANT_ID", str(uuid4()))

    async def boom(*args, **kwargs):
        raise RuntimeError("scan failed")

    monkeypatch.setattr("crepro_erp_reconciliation.main.run_incremental_scan", boom)

    with pytest.raises(RuntimeError, match="scan failed"):
        await run_reconciliation_job()
