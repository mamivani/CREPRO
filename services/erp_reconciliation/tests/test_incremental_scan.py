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
    await ledger_repo.create(
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
    await ledger_repo.create(
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
    last_scan_time = await ledger_repo.get_last_incremental_scan(tenant_id)
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
    """Without an adapter client, a FAILED entry can't be re-posted, so it is reported
    as REPOST_FAILED for manual review."""
    entity_id = uuid4()
    erp_client.add_record("Customer", "CUST-001", platform_id=str(entity_id))
    await ledger_repo.create(
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
async def test_incremental_scan_reposts_failed_entry_from_dlq_payload(
    tenant_id, erp_client, ledger_repo, dlq_repo, adapter_client
):
    entity_id = uuid4()
    payload = {"name": "Acme", "platform_id": str(entity_id)}
    await ledger_repo.create(
        tenant_id=tenant_id, entity_id=entity_id, status="FAILED", erp_docid=None, external_doctype="Customer"
    )
    dlq_event = dlq_repo.add_event(tenant_id=tenant_id, entity_id=entity_id, original_payload=payload)

    report = await run_incremental_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
        dlq_repo=dlq_repo,
        adapter_client=adapter_client,
    )

    assert adapter_client.post_calls[0]["payload"] == payload
    assert report.items_fixed == 1
    assert report.discrepancies_found == 0
    assert ledger_repo.entries[0].status == "POSTED"
    assert ledger_repo.entries[0].erp_docid == "Customer-001"
    assert dlq_event.status == "RECOVERED"


@pytest.mark.asyncio
async def test_incremental_scan_records_repost_rejection_and_increments_attempts(
    tenant_id, erp_client, ledger_repo, dlq_repo
):
    entity_id = uuid4()
    await ledger_repo.create(
        tenant_id=tenant_id, entity_id=entity_id, status="FAILED", erp_docid=None, external_doctype="Customer"
    )
    dlq_repo.add_event(tenant_id=tenant_id, entity_id=entity_id)

    class RejectingAdapterClient:
        async def repost_entity(self, tenant_id, entity_id, external_doctype, payload):
            return False, None

    report = await run_incremental_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
        dlq_repo=dlq_repo,
        adapter_client=RejectingAdapterClient(),
    )

    entry = ledger_repo.entries[0]
    assert entry.status == "FAILED"
    assert entry.attempts == 1
    assert entry.last_error == "Re-post rejected by adapter"
    assert report.manual_review_required == 1
    assert report.discrepancies[0].discrepancy_type == DiscrepancyType.REPOST_FAILED


@pytest.mark.asyncio
async def test_incremental_scan_stops_reposting_after_max_attempts(
    tenant_id, erp_client, ledger_repo, dlq_repo, adapter_client
):
    entity_id = uuid4()
    entry = await ledger_repo.create(
        tenant_id=tenant_id, entity_id=entity_id, status="FAILED", erp_docid=None, external_doctype="Customer"
    )
    entry.attempts = 2
    dlq_repo.add_event(tenant_id=tenant_id, entity_id=entity_id)

    report = await run_incremental_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
        dlq_repo=dlq_repo,
        adapter_client=adapter_client,
    )

    assert adapter_client.post_calls == []
    assert report.manual_review_required == 1


@pytest.mark.asyncio
async def test_incremental_scan_reports_failed_entry_without_dlq_payload(
    tenant_id, erp_client, ledger_repo, dlq_repo, adapter_client
):
    await ledger_repo.create(
        tenant_id=tenant_id, entity_id=uuid4(), status="FAILED", erp_docid=None, external_doctype="Customer"
    )

    report = await run_incremental_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
        dlq_repo=dlq_repo,
        adapter_client=adapter_client,
    )

    assert adapter_client.post_calls == []
    assert report.discrepancies[0].discrepancy_type == DiscrepancyType.REPOST_FAILED


@pytest.mark.asyncio
async def test_incremental_scan_reports_failed_entry_when_adapter_raises(
    tenant_id, erp_client, ledger_repo, dlq_repo
):
    class BoomAdapterClient:
        async def repost_entity(self, tenant_id, entity_id, external_doctype, payload):
            raise RuntimeError("adapter down")

    entity_id = uuid4()
    await ledger_repo.create(
        tenant_id=tenant_id, entity_id=entity_id, status="FAILED", erp_docid=None, external_doctype="Customer"
    )
    dlq_repo.add_event(tenant_id=tenant_id, entity_id=entity_id)

    report = await run_incremental_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
        dlq_repo=dlq_repo,
        adapter_client=BoomAdapterClient(),
    )

    assert report.items_fixed == 0
    assert report.discrepancies[0].discrepancy_type == DiscrepancyType.REPOST_FAILED
