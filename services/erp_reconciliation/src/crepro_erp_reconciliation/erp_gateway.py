"""Read-only ERP gateway that adapts the ERP client to the reconciliation scans' contract.

The scans work with normalized records: each carries its ``doctype``, the platform ID
as a ``platform_id`` string, a datetime ``modified_at`` and a string ``docstatus``.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

PLATFORM_ID_FIELD = "custom_platform_id"
EPOCH = "1970-01-01 00:00:00"
FRAPPE_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DOCSTATUS_NAMES = {0: "Draft", 1: "Submitted", 2: "Cancelled"}


class ERPReadGateway:
    """Wraps a single-ERP client. ``tenant_id`` is accepted for the scans' contract but
    the underlying ERP endpoint is shared, so it is not used to route requests yet."""

    def __init__(self, erp_client: Any) -> None:
        self._erp = erp_client

    async def query_modified_records(
        self,
        tenant_id: UUID,
        modified_after: datetime | None,
        doctypes: list[str],
    ) -> list[dict[str, Any]]:
        since = modified_after.strftime(FRAPPE_DATETIME_FORMAT) if modified_after else EPOCH
        records: list[dict[str, Any]] = []
        for doctype in doctypes:
            rows = await self._erp.get_modified_since(doctype, since)
            records.extend(_normalize(doctype, row) for row in rows)
        return records

    async def query_all_records(self, tenant_id: UUID, doctypes: list[str]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for doctype in doctypes:
            rows = await self._erp.get_all(doctype)
            records.extend(_normalize(doctype, row) for row in rows)
        return records

    async def get_record(
        self, tenant_id: UUID, doctype: str | None, docid: str | None
    ) -> dict[str, Any] | None:
        if not doctype or not docid:
            return None
        row = await self._erp.get_by_name(doctype, docid)
        return _normalize(doctype, row) if row is not None else None


def platform_uuid(erp_record: dict[str, Any]) -> UUID | None:
    """Return the record's platform ID as a UUID, or None if it was not created by the platform."""
    value = erp_record.get("platform_id")
    if not value:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _normalize(doctype: str, row: dict[str, Any]) -> dict[str, Any]:
    docstatus = row.get("docstatus")
    return {
        "doctype": doctype,
        "name": row.get("name"),
        "platform_id": row.get(PLATFORM_ID_FIELD),
        "modified_at": _parse_frappe_datetime(row.get("modified")),
        "docstatus": DOCSTATUS_NAMES.get(docstatus, docstatus),
    }


def _parse_frappe_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).replace(tzinfo=UTC)
    except ValueError:
        return None
