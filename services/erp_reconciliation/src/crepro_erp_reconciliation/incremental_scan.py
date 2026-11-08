"""Incremental reconciliation scan (runs every 15 minutes)."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from .erp_gateway import platform_uuid
from .models import DiscrepancyType, ReconciliationDiscrepancy, ScanReport

logger = logging.getLogger(__name__)

# Matches the DLQ replay cap, so both paths give up on the same entry.
MAX_REPOST_ATTEMPTS = 2


def _as_utc(value: datetime) -> datetime:
    """Treat naive datetimes as UTC so ERP (naive) and ledger (aware) values compare safely."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


async def run_incremental_scan(
    tenant_id: UUID,
    erp_client,
    ledger_repo,
    dlq_repo,
    adapter_client=None,
) -> ScanReport:
    """
    Run incremental reconciliation scan for a tenant.

    Checks for recently modified ERP records and verifies ledger consistency.
    Re-posts FAILED entries via the adapter and detects external modifications.

    Args:
        tenant_id: Tenant to reconcile
        erp_client: ERP API client
        ledger_repo: Adapter ledger repository
        dlq_repo: DLQ event repository
        adapter_client: Adapter service client used to re-post FAILED entries;
            without it, FAILED entries are reported for manual review

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
        last_scan_time = await ledger_repo.get_last_incremental_scan(tenant_id)

        # Query ERP for records modified since last_scan_time
        erp_records = await erp_client.query_modified_records(
            tenant_id=tenant_id,
            modified_after=last_scan_time,
            doctypes=["Customer", "Supplier", "Sales Invoice", "Payment Entry", "Journal Entry"],
        )

        total_records_scanned = len(erp_records)
        logger.info(f"Incremental scan found {total_records_scanned} modified records for tenant {tenant_id}")

        for erp_record in erp_records:
            platform_id = platform_uuid(erp_record)
            # Records without a platform_id were not created by CREPRO, so there is no ledger row to find
            ledger_entry = (
                await ledger_repo.get_by_platform_id(tenant_id=tenant_id, platform_id=platform_id)
                if platform_id
                else None
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

                if platform_id is None:
                    # Nothing to key a ledger row on; a human has to decide what this record is
                    logger.warning(
                        f"ERP record {erp_record.get('name')} has no platform_id in tenant {tenant_id}; "
                        "requires manual intervention"
                    )
                    continue

                # Create ledger entry for this orphaned record
                await ledger_repo.create(
                    tenant_id=tenant_id,
                    entity_id=platform_id,
                    status="RECONCILED",
                    erp_docid=erp_record.get("name"),
                    external_doctype=erp_record.get("doctype"),
                    attempts=0,
                    notes="Created during incremental reconciliation scan",
                )
                items_fixed += 1

            elif ledger_entry.status == "POSTED":
                # Verify record still matches expected state
                if erp_record.get("modified_at") and ledger_entry.updated_at:
                    if _as_utc(erp_record["modified_at"]) > _as_utc(ledger_entry.updated_at):
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

        # FAILED entries never reached ERP, so they won't appear in the modified-since query above.
        # Re-post them from the DLQ payload instead.
        repost_fixed, repost_discrepancies = await _repost_failed_entries(
            tenant_id=tenant_id,
            ledger_repo=ledger_repo,
            dlq_repo=dlq_repo,
            adapter_client=adapter_client,
        )
        items_fixed += repost_fixed
        discrepancies.extend(repost_discrepancies)
        manual_review_required += len(repost_discrepancies)

        # Record scan completion for this tenant
        await ledger_repo.update_last_incremental_scan(tenant_id, datetime.utcnow())

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


async def _repost_failed_entries(
    tenant_id: UUID,
    ledger_repo,
    dlq_repo,
    adapter_client,
) -> tuple[int, list[ReconciliationDiscrepancy]]:
    """Re-post every FAILED ledger entry for a tenant.

    Returns the number recovered and a REPOST_FAILED discrepancy for each one that wasn't.
    """
    recovered = 0
    discrepancies: list[ReconciliationDiscrepancy] = []

    failed_entries = await ledger_repo.get_all(tenant_id, ["FAILED"])
    for entry in failed_entries:
        if await _attempt_repost(tenant_id, entry, ledger_repo, dlq_repo, adapter_client):
            recovered += 1
            continue
        discrepancies.append(
            ReconciliationDiscrepancy(
                id=UUID(int=0),
                tenant_id=tenant_id,
                doctype=entry.external_doctype,
                docid=entry.erp_docid or "Unknown",
                discrepancy_type=DiscrepancyType.REPOST_FAILED,
                detected_at=datetime.utcnow(),
            )
        )

    return recovered, discrepancies


async def _attempt_repost(
    tenant_id: UUID,
    entry,
    ledger_repo,
    dlq_repo,
    adapter_client,
) -> bool:
    """
    Re-post one FAILED ledger entry using the payload from its latest DLQ event.

    The adapter's /api/repost is idempotent (it checks platform_id first), so a
    repost cannot create a duplicate ERP document.

    Returns:
        True if the entry was re-posted and the ledger updated, False otherwise
    """
    if adapter_client is None or dlq_repo is None:
        logger.warning(f"Cannot re-post entity {entry.entity_id}: no adapter client or DLQ repo configured")
        return False

    if entry.attempts >= MAX_REPOST_ATTEMPTS:
        logger.warning(
            f"Entity {entry.entity_id} reached {MAX_REPOST_ATTEMPTS} re-post attempts; needs manual review"
        )
        return False

    try:
        dlq_event = await dlq_repo.get_latest_for_entity(tenant_id, entry.entity_id)
        if dlq_event is None:
            logger.warning(f"No DLQ payload found for FAILED entity {entry.entity_id}")
            return False

        success, erp_docid = await adapter_client.repost_entity(
            tenant_id, entry.entity_id, entry.external_doctype, dlq_event.original_payload
        )
        attempts = entry.attempts + 1

        if not success:
            await ledger_repo.update(entry.id, attempts=attempts, last_error="Re-post rejected by adapter")
            return False

        await ledger_repo.update(
            entry.id,
            status="POSTED",
            erp_docid=erp_docid or entry.erp_docid,
            attempts=attempts,
            last_error=None,
        )
        await dlq_repo.update(dlq_event.id, status="RECOVERED", last_retry_at=datetime.utcnow())
        logger.info(f"Re-posted FAILED entity {entry.entity_id} for tenant {tenant_id}")
        return True

    except Exception as e:
        logger.error(f"Error re-posting entity {entry.entity_id}: {e}")
        return False
