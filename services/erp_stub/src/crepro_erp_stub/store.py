"""In-memory record store for the ERP stub, keyed by doctype."""

import itertools
from datetime import UTC, datetime
from typing import Any

# Mirrors the doctype -> auto-number prefix convention used by erp_adapter's
# mappings.py (Customer, Supplier, Sales Invoice, Payment Entry, Journal Entry)
# plus Property, which push.py's doctype_map also routes to the external ERP.
_DOCTYPE_PREFIXES = {
    "Customer": "CUST",
    "Supplier": "SUPP",
    "Property": "PROP",
    "Sales Invoice": "SINV",
    "Payment Entry": "PAY",
    "Journal Entry": "JE",
}


class ErpStore:
    """Per-doctype record storage with auto-numbered names, mirroring ERPNext's
    `/api/resource/{doctype}` surface closely enough for erp_client.py's calls."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, dict[str, Any]]] = {}
        self._counters: dict[str, itertools.count] = {}

    def reset(self) -> None:
        self._records.clear()
        self._counters.clear()

    def _next_name(self, doctype: str) -> str:
        counter = self._counters.setdefault(doctype, itertools.count(1))
        prefix = _DOCTYPE_PREFIXES.get(doctype, doctype.upper().replace(" ", "-")[:4])
        return f"{prefix}-{next(counter):04d}"

    def create(self, doctype: str, payload: dict[str, Any]) -> dict[str, Any]:
        bucket = self._records.setdefault(doctype, {})
        name = self._next_name(doctype)
        record = {**payload, "name": name, "modified": datetime.now(UTC).isoformat()}
        bucket[name] = record
        return record

    def get(self, doctype: str, name: str) -> dict[str, Any] | None:
        return self._records.get(doctype, {}).get(name)

    def update(self, doctype: str, name: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        record = self._records.get(doctype, {}).get(name)
        if record is None:
            return None
        record.update(updates)
        record["modified"] = datetime.now(UTC).isoformat()
        return record

    def delete(self, doctype: str, name: str) -> bool:
        return self._records.get(doctype, {}).pop(name, None) is not None

    def list_all(self, doctype: str) -> list[dict[str, Any]]:
        return list(self._records.get(doctype, {}).values())


store = ErpStore()
