"""Test fixtures and utilities for reconciliation tests."""

import pytest
from datetime import datetime
from uuid import UUID, uuid4


class MockERPRecord:
    """Mock ERP record."""

    def __init__(self, doctype, name, platform_id=None, modified_at=None, docstatus="Submitted"):
        self.doctype = doctype
        self.name = name
        self.platform_id = platform_id or str(uuid4())
        self.modified_at = modified_at or datetime.utcnow()
        self.docstatus = docstatus

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __contains__(self, key):
        return hasattr(self, key)


class MockLedgerEntry:
    """Mock ledger entry."""

    def __init__(
        self,
        id=None,
        tenant_id=None,
        entity_id=None,
        status="POSTED",
        erp_docid="CUST-001",
        external_doctype="Customer",
        attempts=0,
        created_at=None,
        updated_at=None,
    ):
        self.id = id or uuid4()
        self.tenant_id = tenant_id or uuid4()
        self.entity_id = entity_id or uuid4()
        self.status = status
        self.erp_docid = erp_docid
        self.external_doctype = external_doctype
        self.attempts = attempts
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()


class MockDLQEvent:
    """Mock DLQ event."""

    def __init__(
        self,
        id=None,
        tenant_id=None,
        original_event_id=None,
        entity_id=None,
        external_doctype="Customer",
        original_payload=None,
        status="PENDING",
        routed_at=None,
        dlq_replay_attempts=0,
    ):
        self.id = id or uuid4()
        self.tenant_id = tenant_id or uuid4()
        self.original_event_id = original_event_id or uuid4()
        self.entity_id = entity_id or uuid4()
        self.external_doctype = external_doctype
        self.original_payload = original_payload or {"name": "Test"}
        self.status = status
        self.routed_at = routed_at or datetime.utcnow()
        self.dlq_replay_attempts = dlq_replay_attempts


class MockERPClient:
    """Mock ERP client."""

    def __init__(self):
        self.records = []
        self.query_calls = 0
        self.get_calls = 0

    async def query_modified_records(self, tenant_id, modified_after, doctypes):
        self.query_calls += 1
        return self.records

    async def query_all_records(self, tenant_id, doctypes):
        return self.records

    async def get_record(self, tenant_id, doctype, docid):
        self.get_calls += 1
        for record in self.records:
            if record.get("name") == docid and record.get("doctype") == doctype:
                return record
        return None

    def add_record(self, doctype, name, platform_id=None, modified_at=None, docstatus="Submitted"):
        record = MockERPRecord(doctype, name, platform_id, modified_at, docstatus)
        self.records.append(record)
        return record


class MockLedgerRepo:
    """Mock ledger repository."""

    def __init__(self):
        self.entries = []
        self.last_incremental_scan = {}
        self.last_full_scan = {}

    def get_by_platform_id(self, tenant_id, platform_id):
        from uuid import UUID
        # Normalize to UUID for comparison
        if isinstance(platform_id, str):
            try:
                platform_id = UUID(platform_id)
            except (ValueError, TypeError):
                pass
        
        for entry in self.entries:
            entry_id = entry.entity_id
            if isinstance(entry_id, str):
                try:
                    entry_id = UUID(entry_id)
                except (ValueError, TypeError):
                    pass
            
            if entry_id == platform_id and entry.tenant_id == tenant_id:
                return entry
        return None

    def create(self, tenant_id, entity_id, status, erp_docid, external_doctype, attempts=0, notes="", created_at=None, updated_at=None):
        entry = MockLedgerEntry(
            tenant_id=tenant_id,
            entity_id=entity_id,
            status=status,
            erp_docid=erp_docid,
            external_doctype=external_doctype,
            attempts=attempts,
            created_at=created_at,
            updated_at=updated_at,
        )
        self.entries.append(entry)
        return entry

    def get_last_incremental_scan(self, tenant_id):
        return self.last_incremental_scan.get(tenant_id)

    def update_last_incremental_scan(self, tenant_id, timestamp):
        self.last_incremental_scan[tenant_id] = timestamp

    def get_last_full_scan(self, tenant_id):
        return self.last_full_scan.get(tenant_id)

    def update_last_full_scan(self, tenant_id, timestamp):
        self.last_full_scan[tenant_id] = timestamp

    def get_all(self, tenant_id, statuses):
        return [e for e in self.entries if e.tenant_id == tenant_id and e.status in statuses]

    def update(self, entry_id, **kwargs):
        for entry in self.entries:
            if entry.id == entry_id:
                for key, value in kwargs.items():
                    if hasattr(entry, key):
                        setattr(entry, key, value)
                return entry
        return None


class MockDLQRepo:
    """Mock DLQ repository."""

    def __init__(self):
        self.events = []

    def add_event(self, **kwargs):
        event = MockDLQEvent(**kwargs)
        self.events.append(event)
        return event

    def get_pending_events(self, tenant_id, routed_after, status):
        return [
            e
            for e in self.events
            if e.tenant_id == tenant_id and e.status == status and e.routed_at >= routed_after
        ]

    def update(self, event_id, **kwargs):
        for event in self.events:
            if event.id == event_id:
                for key, value in kwargs.items():
                    if hasattr(event, key):
                        setattr(event, key, value)
                return event
        return None


class MockAdapterClient:
    """Mock adapter service client."""

    def __init__(self, success=True):
        self.success = success
        self.post_calls = []

    async def post_to_erp_with_retry(self, tenant_id, entity_id, external_doctype, payload, dlq_replay=False):
        self.post_calls.append(
            {
                "tenant_id": tenant_id,
                "entity_id": entity_id,
                "external_doctype": external_doctype,
                "payload": payload,
                "dlq_replay": dlq_replay,
            }
        )
        if self.success:
            return True, f"{external_doctype}-001"
        else:
            return False, None


@pytest.fixture
def tenant_id():
    return uuid4()


@pytest.fixture
def erp_client():
    return MockERPClient()


@pytest.fixture
def ledger_repo():
    return MockLedgerRepo()


@pytest.fixture
def dlq_repo():
    return MockDLQRepo()


@pytest.fixture
def adapter_client():
    return MockAdapterClient()
