"""API request/response DTOs for the ERP adapter."""

from uuid import UUID

from crepro_erp_adapter.models import AdapterEventType, AdapterLedgerStatus
from pydantic import BaseModel


class AdapterLedgerEntryCreate(BaseModel):
    platform_entity_id: UUID
    event_type: AdapterEventType
    external_doctype: str
    payload_hash: str


class AdapterLedgerEntryUpdate(BaseModel):
    status: AdapterLedgerStatus | None = None
    external_name: str | None = None
    attempts: int | None = None
    last_error: str | None = None


class TenantErpMappingCreate(BaseModel):
    tier: str = "shared"
    external_erp_target: str


class TenantErpMappingUpdate(BaseModel):
    external_erp_target: str | None = None
