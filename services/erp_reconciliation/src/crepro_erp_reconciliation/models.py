"""Data models for ERP reconciliation."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class DiscrepancyType(StrEnum):
    """Types of discrepancies found during reconciliation."""

    MISSING_LEDGER = "missing_ledger"
    ORPHANED_RECORD = "orphaned_record"
    DELETED_BUT_EXISTS = "deleted_but_exists"
    DELETED_IN_ERP = "deleted_in_erp"
    EXTERNAL_MODIFICATION = "external_modification"
    REPOST_FAILED = "repost_failed"


@dataclass
class ReconciliationDiscrepancy:
    """A discrepancy found during reconciliation."""

    id: UUID
    tenant_id: UUID
    doctype: str
    docid: str
    discrepancy_type: DiscrepancyType
    detected_at: datetime
    resolved: bool = False
    resolution_notes: str = ""


@dataclass
class ScanReport:
    """Report of a reconciliation scan run."""

    scan_type: str  # "incremental" or "full"
    tenant_id: UUID
    started_at: datetime
    completed_at: datetime
    total_records_scanned: int
    discrepancies_found: int
    items_fixed: int
    manual_review_required: int
    discrepancies: list[ReconciliationDiscrepancy] = field(default_factory=list)


@dataclass
class DLQReplayReport:
    """Report of a DLQ replay run."""

    tenant_id: UUID
    replay_started_at: datetime
    replay_completed_at: datetime
    dlq_events_attempted: int
    dlq_events_recovered: int
    dlq_events_manual_review: int


@dataclass
class ReconciliationState:
    """Tracks reconciliation state across runs."""

    tenant_id: UUID
    last_incremental_scan_at: datetime | None = None
    last_full_scan_at: datetime | None = None
    last_dlq_replay_at: datetime | None = None
    pending_manual_reviews: int = 0
