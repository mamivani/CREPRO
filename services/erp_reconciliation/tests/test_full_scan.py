"""Tests for full reconciliation scan."""

from uuid import uuid4

import pytest
from crepro_erp_reconciliation.full_scan import run_full_scan
from crepro_erp_reconciliation.models import DiscrepancyType


@pytest.mark.asyncio
async def test_full_scan_finds_no_discrepancies_when_consistent(tenant_id, erp_client, ledger_repo):
    """Full scan finds no issues when all records are consistent."""
    # Setup: Create matching records
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
    report = await run_full_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
    )

    # Assert
    assert report.scan_type == "full"
    assert report.discrepancies_found == 0
    assert report.items_fixed == 0


@pytest.mark.asyncio
async def test_full_scan_detects_orphaned_erp_records(tenant_id, erp_client, ledger_repo):
    """Full scan detects ERP records without ledger entries."""
    # Setup: Add ERP record but no ledger entry
    entity_id = uuid4()
    erp_client.add_record("Customer", "CUST-001", platform_id=str(entity_id))

    # Execute
    report = await run_full_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
    )

    # Assert
    assert report.discrepancies_found == 1
    assert report.items_fixed == 1  # Should create ledger entry
    assert report.discrepancies[0].discrepancy_type == DiscrepancyType.ORPHANED_RECORD


@pytest.mark.asyncio
async def test_full_scan_detects_deleted_in_erp(tenant_id, erp_client, ledger_repo):
    """Full scan detects ledger entries where ERP record was deleted."""
    # Setup: Create ledger entry but no ERP record
    entity_id = uuid4()
    ledger_repo.create(
        tenant_id=tenant_id,
        entity_id=entity_id,
        status="POSTED",
        erp_docid="CUST-001",
        external_doctype="Customer",
    )

    # Execute
    report = await run_full_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
    )

    # Assert
    assert report.discrepancies_found == 1
    assert report.items_fixed == 1  # Should mark as DELETED
    assert report.discrepancies[0].discrepancy_type == DiscrepancyType.DELETED_IN_ERP

    # Verify ledger was updated
    entries = ledger_repo.get_all(tenant_id, ["DELETED"])
    assert len(entries) == 1
    assert entries[0].status == "DELETED"


@pytest.mark.asyncio
async def test_full_scan_detects_deleted_but_exists(tenant_id, erp_client, ledger_repo):
    """Full scan detects when ledger says DELETED but ERP record still exists."""
    # Setup: Create ledger entry marked DELETED, but ERP record still exists
    entity_id = uuid4()
    erp_client.add_record(
        "Customer",
        "CUST-001",
        platform_id=str(entity_id),
        docstatus="Submitted",
    )
    ledger_repo.create(
        tenant_id=tenant_id,
        entity_id=entity_id,
        status="DELETED",
        erp_docid="CUST-001",
        external_doctype="Customer",
    )

    # Execute
    report = await run_full_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
    )

    # Assert
    assert report.discrepancies_found == 1
    assert report.manual_review_required == 1
    assert report.discrepancies[0].discrepancy_type == DiscrepancyType.DELETED_BUT_EXISTS


@pytest.mark.asyncio
async def test_full_scan_updates_last_scan_time(tenant_id, erp_client, ledger_repo):
    """Full scan updates last scan time after completion."""
    # Execute
    report = await run_full_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
    )

    # Assert
    last_scan_time = ledger_repo.get_last_full_scan(tenant_id)
    assert last_scan_time is not None
    assert last_scan_time >= report.started_at
    assert last_scan_time <= report.completed_at


@pytest.mark.asyncio
async def test_full_scan_handles_multiple_discrepancies(tenant_id, erp_client, ledger_repo):
    """Full scan correctly handles multiple discrepancies in one scan."""
    # Setup: Create multiple discrepancy scenarios
    # 1. Orphaned ERP record (no ledger)
    erp_client.add_record("Customer", "CUST-001", platform_id=str(uuid4()))

    # 2. Deleted in ERP (ledger exists but ERP doesn't)
    entity_id_2 = uuid4()
    ledger_repo.create(
        tenant_id=tenant_id,
        entity_id=entity_id_2,
        status="POSTED",
        erp_docid="CUST-002",
        external_doctype="Customer",
    )

    # 3. Consistent record
    entity_id_3 = uuid4()
    erp_client.add_record("Customer", "CUST-003", platform_id=str(entity_id_3))
    ledger_repo.create(
        tenant_id=tenant_id,
        entity_id=entity_id_3,
        status="POSTED",
        erp_docid="CUST-003",
        external_doctype="Customer",
    )

    # Execute
    report = await run_full_scan(
        tenant_id=tenant_id,
        erp_client=erp_client,
        ledger_repo=ledger_repo,
    )

    # Assert
    assert report.total_records_scanned >= 2  # At least 2 ERP records checked (CUST-001, CUST-003)
    assert report.discrepancies_found >= 2  # At least 2 discrepancies (orphaned + deleted in ERP)
    assert report.items_fixed >= 1  # At least 1 item fixed
