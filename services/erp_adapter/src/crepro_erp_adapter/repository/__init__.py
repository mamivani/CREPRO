"""Tenant-scoped in-memory stores for the ERP adapter, ahead of a real database."""

from crepro_common import InMemoryRepository
from crepro_erp_adapter.models import AdapterLedgerEntry, TenantErpMapping

ledger_entries: InMemoryRepository[AdapterLedgerEntry] = InMemoryRepository()
tenant_mappings: InMemoryRepository[TenantErpMapping] = InMemoryRepository()
