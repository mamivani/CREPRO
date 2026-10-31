"""Domain entities for the payment service: payment records and security deposits.

Payments recorded here are the platform's own view of money movement. The external ERP's
ledger is the system of record for accounting; the ERP adapter posts confirmed payments
there asynchronously and records the resulting reference back onto these rows.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from crepro_common import TenantScopedEntity


class PaymentMethod(StrEnum):
    ACH = "ach"
    CARD = "card"
    CHECK = "check"
    CASH = "cash"
    WIRE = "wire"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class SecurityDepositStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    INVOICE_RAISED = "invoice_raised"
    RECEIVED = "received"
    RECEIVED_IN_PART = "received_in_part"
    RETURNED_IN_PART = "returned_in_part"
    RETURNED = "returned"
    RECOVERED_FOR_RENT = "recovered_for_rent"
    RECOVERED_FOR_REPAIRS = "recovered_for_repairs"


class PaymentRecord(TenantScopedEntity):
    """A payment received from or refunded to a resident."""

    lease_id: UUID
    resident_id: UUID
    amount: float
    currency: str = "USD"
    method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PENDING
    reference: str | None = None
    received_at: datetime | None = None
    posted_to_erp: bool = False
    erp_reference: str | None = None


class SecurityDeposit(TenantScopedEntity):
    """The security deposit held against a lease, and its lifecycle."""

    lease_id: UUID
    amount: float
    currency: str = "USD"
    status: SecurityDepositStatus = SecurityDepositStatus.NOT_REQUIRED
    received_payment_id: UUID | None = None
    returned_payment_id: UUID | None = None
