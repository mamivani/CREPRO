"""Tests for the ERP read gateway that adapts ERPClient to the reconciliation scans."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from crepro_erp_reconciliation.erp_gateway import ERPReadGateway, platform_uuid


class FakeERP:
    def __init__(self):
        self.modified_calls = []
        self.all_calls = []
        self.by_name = {}

    async def get_modified_since(self, doctype, since):
        self.modified_calls.append((doctype, since))
        return [
            {
                "name": "CUST-1",
                "custom_platform_id": "abc",
                "modified": "2026-01-02 03:04:05.678",
                "docstatus": 1,
            }
        ]

    async def get_all(self, doctype):
        self.all_calls.append(doctype)
        return [{"name": "CUST-2", "custom_platform_id": None, "modified": None, "docstatus": 0}]

    async def get_by_name(self, doctype, docid):
        return self.by_name.get((doctype, docid))


@pytest.mark.asyncio
async def test_query_modified_records_normalizes_rows() -> None:
    erp = FakeERP()
    gateway = ERPReadGateway(erp)
    since = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

    records = await gateway.query_modified_records(uuid4(), since, ["Customer"])

    assert erp.modified_calls == [("Customer", "2026-01-01 12:00:00")]
    assert records == [
        {
            "doctype": "Customer",
            "name": "CUST-1",
            "platform_id": "abc",
            "modified_at": datetime(2026, 1, 2, 3, 4, 5, 678000, tzinfo=UTC),
            "docstatus": "Submitted",
        }
    ]


@pytest.mark.asyncio
async def test_query_modified_records_uses_epoch_when_no_watermark() -> None:
    erp = FakeERP()
    await ERPReadGateway(erp).query_modified_records(uuid4(), None, ["Customer"])

    assert erp.modified_calls == [("Customer", "1970-01-01 00:00:00")]


@pytest.mark.asyncio
async def test_query_all_records_maps_docstatus_and_missing_fields() -> None:
    erp = FakeERP()
    records = await ERPReadGateway(erp).query_all_records(uuid4(), ["Customer"])

    assert erp.all_calls == ["Customer"]
    assert records[0]["docstatus"] == "Draft"
    assert records[0]["platform_id"] is None
    assert records[0]["modified_at"] is None


@pytest.mark.asyncio
async def test_get_record_returns_none_for_missing_identifiers_or_404() -> None:
    gateway = ERPReadGateway(FakeERP())

    assert await gateway.get_record(uuid4(), None, "CUST-1") is None
    assert await gateway.get_record(uuid4(), "Customer", None) is None
    assert await gateway.get_record(uuid4(), "Customer", "MISSING") is None


@pytest.mark.asyncio
async def test_get_record_returns_normalized_row() -> None:
    erp = FakeERP()
    erp.by_name[("Customer", "CUST-1")] = {"name": "CUST-1", "custom_platform_id": None, "docstatus": 2}

    record = await ERPReadGateway(erp).get_record(uuid4(), "Customer", "CUST-1")

    assert record["doctype"] == "Customer"
    assert record["docstatus"] == "Cancelled"


def test_platform_uuid_parses_valid_and_rejects_invalid_values() -> None:
    value = uuid4()

    assert platform_uuid({"platform_id": str(value)}) == value
    assert platform_uuid({"platform_id": "not-a-uuid"}) is None
    assert platform_uuid({"platform_id": None}) is None
    assert platform_uuid({}) is None
