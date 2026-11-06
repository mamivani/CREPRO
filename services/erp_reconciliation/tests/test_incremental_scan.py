"""Tests for incremental reconciliation scan."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from crepro_erp_reconciliation.incremental_scan import run_incremental_scan
from crepro_erp_reconciliation.models import DiscrepancyType


@pytest.mark.asyncio
async def test_incremental_scan_finds_no_discrepancies_when_all_consistent(
    tenant_id, erp_client, ledger_repo
):
    """Incremental scan finds no issues when ledger and ERP are consistent."""
    # Setup: Create matching records in ERP and ledger
    entity_id = uuid4()
    erp_client.add_record("Customer", "CUST-001", platform_id=str(entity_id))
    ledger_repo.create(
        tenant_id=tenant_id,
        entity_id=entity_id,
        status="POSTED",
        erp_docid="CUST-001",
        external_doctype="Customer",
    )

    # Execute
    report = await run_incremental_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
        dlq_repo=None,
    )

    # Assert
    assert report.scan_type == "incremental"
    assert report.discrepancies_found == 0
    assert report.items_fixed == 0
    assert report.manual_review_required == 0


@pytest.mark.asyncio
async def test_incremental_scan_detects_missing_ledger_entry(tenant_id, erp_client, ledger_repo):
    """Incremental scan detects ERP records with missing ledger entries."""
    # Setup: Add ERP record but no ledger entry
    entity_id = uuid4()
    erp_client.add_record("Customer", "CUST-001", platform_id=str(entity_id))

    # Execute
    report = await run_incremental_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
        dlq_repo=None,
    )

    # Assert
    assert report.discrepancies_found == 1
    assert report.items_fixed == 1  # Should create ledger entry
    assert report.manual_review_required == 1  # Still requires review since it's a discrepancy
    assert report.discrepancies[0].discrepancy_type == DiscrepancyType.MISSING_LEDGER


@pytest.mark.asyncio
async def test_incremental_scan_detects_external_modifications(tenant_id, erp_client, ledger_repo):
    """Incremental scan detects when ERP records are modified externally."""
    # Setup: Create records where ERP was modified after ledger update
    entity_id = uuid4()
    ledger_updated = datetime.utcnow() - timedelta(hours=1)
    erp_modified = datetime.utcnow()

    erp_client.add_record(
        "Customer",
        "CUST-001",
        platform_id=str(entity_id),
        modified_at=erp_modified,
    )
    ledger_repo.create(
        tenant_id=tenant_id,
        entity_id=entity_id,
        status="POSTED",
        erp_docid="CUST-001",
        external_doctype="Customer",
        created_at=ledger_updated,
        updated_at=ledger_updated,
    )

    # Execute
    report = await run_incremental_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
        dlq_repo=None,
    )

    # Assert
    assert report.discrepancies_found == 1
    assert report.discrepancies[0].discrepancy_type == DiscrepancyType.EXTERNAL_MODIFICATION
    assert report.manual_review_required == 1


@pytest.mark.asyncio
async def test_incremental_scan_updates_last_scan_time(tenant_id, erp_client, ledger_repo):
    """Incremental scan updates last scan time after completion."""
    # Execute
    report = await run_incremental_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
        dlq_repo=None,
    )

    # Assert
    last_scan_time = ledger_repo.get_last_incremental_scan(tenant_id)
    assert last_scan_time is not None
    assert last_scan_time >= report.started_at
    assert last_scan_time <= report.completed_at


@pytest.mark.asyncio
async def test_incremental_scan_handles_empty_result(tenant_id, erp_client, ledger_repo):
    """Incremental scan handles case with no ERP records."""
    # Execute
    report = await run_incremental_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
        dlq_repo=None,
    )

    # Assert
    assert report.total_records_scanned == 0
    assert report.discrepancies_found == 0
    assert report.items_fixed == 0


@pytest.mark.asyncio
async def test_incremental_scan_reposts_failed_entry_and_records_discrepancy(
    tenant_id, erp_client, ledger_repo
):
    """Incremental scan attempts to re-post FAILED entries. `_attempt_repost` isn't
    fully implemented yet (always returns False, see its docstring), so this
    currently always records a REPOST_FAILED discrepancy for manual review."""
    entity_id = uuid4()
    erp_client.add_record("Customer", "CUST-001", platform_id=str(entity_id))
    ledger_repo.create(
        tenant_id=tenant_id,
        entity_id=entity_id,
        status="FAILED",
        erp_docid="CUST-001",
        external_doctype="Customer",
    )

    # Execute
    report = await run_incremental_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
        dlq_repo=None,
    )

    # Assert
    assert report.discrepancies_found == 1
    assert report.manual_review_required == 1
    assert report.discrepancies[0].discrepancy_type == DiscrepancyType.REPOST_FAILED


@pytest.mark.asyncio
async def test_incremental_scan_reraises_erp_client_errors(tenant_id, ledger_repo):
    """Incremental scan logs and re-raises errors from the ERP client, rather than
    swallowing them -- it must not record a false 'clean' scan."""

    class BoomERPClient:
        async def query_modified_records(self, **kwargs):
            raise RuntimeError("ERP unreachable")

    with pytest.raises(RuntimeError, match="ERP unreachable"):
        await run_incremental_scan(
            tenant_id=tenant_id,
            erp_client=BoomERPClient(),
            ledger_repo=ledger_repo,
            dlq_repo=None,
        )


@pytest.mark.asyncio
async def test_attempt_repost_returns_false_on_unexpected_error(monkeypatch, tenant_id):
    """`_attempt_repost`'s except branch is defensive: even if logging itself
    somehow raised, repost must still resolve to False, not propagate."""
    from crepro_erp_reconciliation import incremental_scan as module

    def boom_warning(*args, **kwargs):
        raise RuntimeError("logging backend down")

    monkeypatch.setattr(module.logger, "warning", boom_warning)

    result = await module._attempt_repost(
        tenant_id=tenant_id,
        entity_id=uuid4(),
        erp_client=None,
        ledger_repo=None,
        ledger_entry=None,
    )

    assert result is False
