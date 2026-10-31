"""Domain entities for the ERP adapter: the only service allowed to call the external ERP.

Mirrors docs/design/erp-adapter-hybrid.md: an append-only ledger of what has been posted
to the external ERP (for idempotency and audit) and a per-tenant mapping to that ERP's
target company/site. Field and doctype names here are generic accounting vocabulary
(Customer, Supplier, Sales Invoice, Payment Entry, Journal Entry, Mode of Payment), not a
reference to any specific ERP product.
"""

from enum import StrEnum
from uuid import UUID

from crepro_common import TenantScopedEntity


class AdapterEventType(StrEnum):
    CUSTOMER_UPSERTED = "customer_upserted"
    VENDOR_UPSERTED = "vendor_upserted"
    INVOICE_GENERATED = "invoice_generated"
    PAYMENT_POSTED = "payment_posted"
    DEPOSIT_RECORDED = "deposit_recorded"
    ADJUSTMENT_POSTED = "adjustment_posted"
    PAYMENT_METHOD_CONFIGURED = "payment_method_configured"


class AdapterLedgerStatus(StrEnum):
    PENDING = "pending"
    POSTED = "posted"
    FAILED = "failed"


class AdapterLedgerEntry(TenantScopedEntity):
    """The adapter's own audit trail of what it has posted, keyed by platform_id for idempotency."""

    platform_entity_id: UUID
    event_type: AdapterEventType
    external_doctype: str
    external_name: str | None = None
    payload_hash: str
    status: AdapterLedgerStatus = AdapterLedgerStatus.PENDING
    attempts: int = 0
    last_error: str | None = None


class TenantErpMapping(TenantScopedEntity):
    """Which external ERP target (company or site) a tenant's records post to."""

    tier: str = "shared"
    external_erp_target: str
