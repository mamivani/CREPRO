"""API request/response DTOs for the payment service."""

from datetime import datetime
from uuid import UUID

from crepro_payment.models import PaymentMethod, PaymentStatus, SecurityDepositStatus
from pydantic import BaseModel


class PaymentRecordCreate(BaseModel):
    lease_id: UUID
    resident_id: UUID
    amount: float
    currency: str = "USD"
    method: PaymentMethod
    reference: str | None = None
    received_at: datetime | None = None


class PaymentRecordUpdate(BaseModel):
    status: PaymentStatus | None = None
    posted_to_erp: bool | None = None
    erp_reference: str | None = None


class SecurityDepositCreate(BaseModel):
    lease_id: UUID
    amount: float
    currency: str = "USD"
    status: SecurityDepositStatus = SecurityDepositStatus.NOT_REQUIRED


class SecurityDepositUpdate(BaseModel):
    status: SecurityDepositStatus | None = None
    received_payment_id: UUID | None = None
    returned_payment_id: UUID | None = None
