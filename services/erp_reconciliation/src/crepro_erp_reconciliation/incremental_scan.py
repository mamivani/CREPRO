"""Incremental reconciliation scan (runs every 15 minutes)."""

import logging
from datetime import datetime
from uuid import UUID

from crepro_common import EventEnvelope

from .models import ReconciliationDiscrepancy, ScanReport, DiscrepancyType

logger = logging.getLogger(__name__)


async def run_incremental_scan(
    tenant_id: UUID,
    erp_client,
    ledger_repo,
    dlq_repo,
) -> ScanReport:
    """
    Run incremental reconciliation scan for a tenant.

    Checks for recently modified ERP records and verifies ledger consistency.
    Attempts to re-post FAILED entries and detects external modifications.

    Args:
        tenant_id: Tenant to reconcile
        erp_client: ERP API client
        ledger_repo: Adapter ledger repository
        dlq_repo: DLQ event repository

    Returns:
        ScanReport with results
    """
    started_at = datetime.utcnow()
    discrepancies: list[ReconciliationDiscrepancy] = []
    items_fixed = 0
    manual_review_required = 0
    total_records_scanned = 0

    try:
        # Get last scan time for this tenant
        last_scan_time = ledger_repo.get_last_incremental_scan(tenant_id)

        # Query ERP for records modified since last_scan_time
        erp_records = await erp_client.query_modified_records(
            tenant_id=tenant_id,
            modified_after=last_scan_time,
            doctypes=["Customer", "Supplier", "Sales Invoice", "Payment Entry", "Journal Entry"],
        )

        total_records_scanned = len(erp_records)
        logger.info(f"Incremental scan found {total_records_scanned} modified records for tenant {tenant_id}")

        for erp_record in erp_records:
            # Check if we have a ledger entry for this record
            ledger_entry = ledger_repo.get_by_platform_id(
                tenant_id=tenant_id,
                platform_id=erp_record.get("platform_id"),
            )

            if ledger_entry is None:
                # Missing ledger entry - shouldn't happen, but record it
                discrepancy = ReconciliationDiscrepancy(
                    id=UUID(int=0),
                    tenant_id=tenant_id,
                    doctype=erp_record.get("doctype", "Unknown"),
                    docid=erp_record.get("name", "Unknown"),
                    discrepancy_type=DiscrepancyType.MISSING_LEDGER,
                    detected_at=datetime.utcnow(),
                )
                discrepancies.append(discrepancy)
                manual_review_required += 1

                # Create ledger entry for this orphaned record
                ledger_repo.create(
                    tenant_id=tenant_id,
                    entity_id=erp_record.get("platform_id"),
                    status="RECONCILED",
                    erp_docid=erp_record.get("name"),
                    external_doctype=erp_record.get("doctype"),
                    attempts=0,
                    notes="Created during incremental reconciliation scan",
                )
                items_fixed += 1

            elif ledger_entry.status == "FAILED":
                # Previous attempt failed - attempt re-post
                logger.info(f"Re-posting failed entry {ledger_entry.entity_id} for tenant {tenant_id}")

                # Re-post to ERP (this would call post_to_erp_with_retry from adapter)
                # For now, we'll mark as attempted
                success = await _attempt_repost(
                    tenant_id=tenant_id,
                    entity_id=ledger_entry.entity_id,
                    erp_client=erp_client,
                    ledger_repo=ledger_repo,
                    ledger_entry=ledger_entry,
                )

                if success:
                    items_fixed += 1
                else:
                    discrepancy = ReconciliationDiscrepancy(
                        id=UUID(int=0),
                        tenant_id=tenant_id,
                        doctype=ledger_entry.external_doctype,
                        docid=ledger_entry.erp_docid or "Unknown",
                        discrepancy_type=DiscrepancyType.REPOST_FAILED,
                        detected_at=datetime.utcnow(),
                    )
                    discrepancies.append(discrepancy)
                    manual_review_required += 1

            elif ledger_entry.status == "POSTED":
                # Verify record still matches expected state
                if erp_record.get("modified_at") and ledger_entry.updated_at:
                    if erp_record.get("modified_at") > ledger_entry.updated_at:
                        # ERP record was modified after we posted it
                        discrepancy = ReconciliationDiscrepancy(
                            id=UUID(int=0),
                            tenant_id=tenant_id,
                            doctype=erp_record.get("doctype", "Unknown"),
                            docid=erp_record.get("name", "Unknown"),
                            discrepancy_type=DiscrepancyType.EXTERNAL_MODIFICATION,
                            detected_at=datetime.utcnow(),
                            resolution_notes="ERP record was modified externally after posting",
                        )
                        discrepancies.append(discrepancy)
                        manual_review_required += 1

        # Record scan completion for this tenant
        ledger_repo.update_last_incremental_scan(tenant_id, datetime.utcnow())

    except Exception as e:
        logger.error(f"Error during incremental scan for tenant {tenant_id}: {e}", exc_info=True)
        raise

    completed_at = datetime.utcnow()

    report = ScanReport(
        scan_type="incremental",
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
        f"Incremental scan complete for tenant {tenant_id}: "
        f"scanned={total_records_scanned}, fixed={items_fixed}, "
        f"manual_review={manual_review_required}"
    )

    return report


async def _attempt_repost(
    tenant_id: UUID,
    entity_id: UUID,
    erp_client,
    ledger_repo,
    ledger_entry,
) -> bool:
    """
    Attempt to re-post a failed entry to ERP.

    Args:
        tenant_id: Tenant ID
        entity_id: Entity ID
        erp_client: ERP client
        ledger_repo: Ledger repository
        ledger_entry: The failed ledger entry

    Returns:
        True if re-post succeeded, False otherwise
    """
    try:
        # In production, this would reconstruct the original payload from our domain model
        # For now, we'll just mark as attempted
        logger.warning(f"Repost not fully implemented for entity {entity_id}; marking for manual review")
        return False
    except Exception as e:
        logger.error(f"Error re-posting entity {entity_id}: {e}")
        return False
