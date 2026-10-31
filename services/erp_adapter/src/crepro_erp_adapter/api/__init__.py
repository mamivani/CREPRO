"""HTTP routes for the ERP adapter.

These expose the adapter ledger and tenant mapping table for inspection and manual repair.
The actual push (Service Bus subscriber) and pull (reconciliation job) paths described in
docs/design/erp-adapter-hybrid.md are separate workers, not HTTP endpoints, and are out of
scope for this scaffold.
"""

from crepro_common import build_crud_router
from crepro_erp_adapter.models import AdapterLedgerEntry, TenantErpMapping
from crepro_erp_adapter.repository import ledger_entries, tenant_mappings
from crepro_erp_adapter.schemas import (
    AdapterLedgerEntryCreate,
    AdapterLedgerEntryUpdate,
    TenantErpMappingCreate,
    TenantErpMappingUpdate,
)
from fastapi import APIRouter

router = APIRouter()

router.include_router(
    build_crud_router(
        prefix="/api/v1/ledger-entries",
        tags=["ledger-entries"],
        repository=ledger_entries,
        entity_cls=AdapterLedgerEntry,
        create_schema=AdapterLedgerEntryCreate,
        update_schema=AdapterLedgerEntryUpdate,
        not_found_detail="Ledger entry not found",
    )
)

router.include_router(
    build_crud_router(
        prefix="/api/v1/tenant-mappings",
        tags=["tenant-mappings"],
        repository=tenant_mappings,
        entity_cls=TenantErpMapping,
        create_schema=TenantErpMappingCreate,
        update_schema=TenantErpMappingUpdate,
        not_found_detail="Tenant mapping not found",
    )
)
