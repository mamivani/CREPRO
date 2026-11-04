"""Full reconciliation scan (runs nightly)."""

import logging
from datetime import datetime
from uuid import UUID

from .models import ReconciliationDiscrepancy, ScanReport, DiscrepancyType

logger = logging.getLogger(__name__)


async def run_full_scan(
    tenant_id: UUID,
    erp_client,
    ledger_repo,
) -> ScanReport:
    """
    Run full reconciliation scan for a tenant.

    Queries ALL external records and verifies ledger completeness.
    Detects orphaned ERP records and verifies all ledger entries have corresponding ERP records.

    Args:
        tenant_id: Tenant to reconcile
        erp_client: ERP API client
        ledger_repo: Adapter ledger repository

    Returns:
        ScanReport with results
    """
    started_at = datetime.utcnow()
    discrepancies: list[ReconciliationDiscrepancy] = []
    items_fixed = 0
    manual_review_required = 0
    total_records_scanned = 0

    try:
        # Query ALL external records (not just recent modifications)
        all_erp_records = await erp_client.query_all_records(
            tenant_id=tenant_id,
            doctypes=["Customer", "Supplier", "Sales Invoice", "Payment Entry", "Journal Entry"],
        )

        total_records_scanned = len(all_erp_records)
        logger.info(f"Full scan found {total_records_scanned} total records for tenant {tenant_id}")

        # Step 1: Check all ERP records have ledger entries
        for erp_record in all_erp_records:
            ledger_entry = ledger_repo.get_by_platform_id(
                tenant_id=tenant_id,
                platform_id=erp_record.get("platform_id"),
            )

            if ledger_entry is None:
                # Orphaned ERP record - no corresponding ledger entry
                discrepancy = ReconciliationDiscrepancy(
                    id=UUID(int=0),
                    tenant_id=tenant_id,
                    doctype=erp_record.get("doctype", "Unknown"),
                    docid=erp_record.get("name", "Unknown"),
                    discrepancy_type=DiscrepancyType.ORPHANED_RECORD,
                    detected_at=datetime.utcnow(),
                )
                discrepancies.append(discrepancy)

                # Try to reconstruct ledger entry from ERP data
                if _can_infer_source(erp_record):
                    try:
                        ledger_repo.create(
                            tenant_id=tenant_id,
                            entity_id=erp_record.get("platform_id"),
                            status="RECONCILED",
                            erp_docid=erp_record.get("name"),
                            external_doctype=erp_record.get("doctype"),
                            attempts=0,
                            notes="Inferred from ERP during full scan",
                        )
                        items_fixed += 1
                    except Exception as e:
                        logger.error(f"Error creating inferred ledger entry: {e}")
                        manual_review_required += 1
                else:
                    # Cannot infer - mark for manual review
                    manual_review_required += 1
                    logger.warning(
                        f"Cannot infer source for orphaned ERP record {erp_record.get('name')} "
                        f"in tenant {tenant_id}; requires manual intervention"
                    )

            elif ledger_entry.status == "DELETED":
                # We deleted it but ERP still has it active
                if erp_record.get("docstatus") != "Cancelled":
                    discrepancy = ReconciliationDiscrepancy(
                        id=UUID(int=0),
                        tenant_id=tenant_id,
                        doctype=erp_record.get("doctype", "Unknown"),
                        docid=erp_record.get("name", "Unknown"),
                        discrepancy_type=DiscrepancyType.DELETED_BUT_EXISTS,
                        detected_at=datetime.utcnow(),
                        resolution_notes="Record marked deleted in ledger but still active in ERP",
                    )
                    discrepancies.append(discrepancy)
                    manual_review_required += 1

        # Step 2: Check all ledger entries have corresponding ERP records
        all_ledger_entries = ledger_repo.get_all(
            tenant_id=tenant_id,
            statuses=["POSTED", "FAILED"],
        )

        for ledger_entry in all_ledger_entries:
            erp_record = await erp_client.get_record(
                tenant_id=tenant_id,
                doctype=ledger_entry.external_doctype,
                docid=ledger_entry.erp_docid,
            )

            if erp_record is None:
                # We think we posted it but ERP doesn't have it anymore
                discrepancy = ReconciliationDiscrepancy(
                    id=UUID(int=0),
                    tenant_id=tenant_id,
                    doctype=ledger_entry.external_doctype,
                    docid=ledger_entry.erp_docid,
                    discrepancy_type=DiscrepancyType.DELETED_IN_ERP,
                    detected_at=datetime.utcnow(),
                    resolution_notes="Ledger entry exists but ERP record is missing",
                )
                discrepancies.append(discrepancy)
                manual_review_required += 1

                # Mark as deleted in ledger
                ledger_repo.update(
                    ledger_entry.id,
                    status="DELETED",
                    updated_at=datetime.utcnow(),
                )
                items_fixed += 1

        # Record scan completion for this tenant
        ledger_repo.update_last_full_scan(tenant_id, datetime.utcnow())

    except Exception as e:
        logger.error(f"Error during full scan for tenant {tenant_id}: {e}", exc_info=True)
        raise

    completed_at = datetime.utcnow()

    report = ScanReport(
        scan_type="full",
        tenant_id=tenant_id,
        started_at=started_at,
        completed_at=completed_at,
        total_records_scanned=total_records_scanned,
        discrepancies_found=len(discrepancies),
        items_fixed=items_fixed,
        manual_review_required=manual_review_required,
        discrepancies=discrepancies,
    )

    logger.info(
        f"Full scan complete for tenant {tenant_id}: "
        f"scanned={total_records_scanned}, fixed={items_fixed}, "
        f"manual_review={manual_review_required}"
    )

    return report


def _can_infer_source(erp_record: dict) -> bool:
    """
    Check if we can infer the source of an orphaned ERP record.

    Args:
        erp_record: ERP record data

    Returns:
        True if we can infer source, False otherwise
    """
    # Check if record has platform_id (custom field we added)
    # If it does, we can infer it came from CREPRO
    return "platform_id" in erp_record and erp_record.get("platform_id") is not None
