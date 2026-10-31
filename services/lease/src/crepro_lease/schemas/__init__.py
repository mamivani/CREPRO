"""API request/response DTOs for the lease service."""

from datetime import date
from uuid import UUID

from crepro_lease.models import (
    ChargeBasis,
    ExitType,
    IncrementType,
    IncrementUnit,
    LeaseFrequency,
    LeaseStatus,
    ResidentStatus,
    ResidentType,
    SecurityDepositStatus,
)
from pydantic import BaseModel


class LeaseCreate(BaseModel):
    property_id: UUID
    unit_id: UUID
    resident_id: UUID
    start_date: date
    end_date: date
    frequency: LeaseFrequency = LeaseFrequency.MONTHLY
    status: LeaseStatus = LeaseStatus.DRAFT
    notice_period_days: int = 30
    fit_out_period_days: int = 0
    security_deposit_amount: float = 0
    security_deposit_currency: str = "USD"
    security_deposit_status: SecurityDepositStatus = SecurityDepositStatus.NOT_REQUIRED
    late_payment_interest_percent: float = 0
    renewed_from_id: UUID | None = None


class LeaseUpdate(BaseModel):
    end_date: date | None = None
    status: LeaseStatus | None = None
    security_deposit_status: SecurityDepositStatus | None = None
    late_payment_interest_percent: float | None = None


class LeaseChargeCreate(BaseModel):
    lease_id: UUID
    charge_code: str
    description: str | None = None
    frequency: LeaseFrequency = LeaseFrequency.MONTHLY
    amount: float
    currency: str = "USD"
    charge_basis: ChargeBasis = ChargeBasis.FIXED
    withholding_tax_percent: float = 0
    valid_from: date
    is_active: bool = True


class LeaseChargeUpdate(BaseModel):
    amount: float | None = None
    is_active: bool | None = None


class LeaseIncrementRuleCreate(BaseModel):
    lease_id: UUID
    charge_code: str
    increment_every: int
    increment_unit: IncrementUnit
    increment_type: IncrementType
    increment_value: float
    effective_from: date
    is_active: bool = True


class LeaseIncrementRuleUpdate(BaseModel):
    increment_value: float | None = None
    is_active: bool | None = None


class LeaseExitCreate(BaseModel):
    lease_id: UUID
    exit_type: ExitType
    effective_date: date
    details: str | None = None


class LeaseExitUpdate(BaseModel):
    details: str | None = None


class ResidentCreate(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    resident_type: ResidentType = ResidentType.PRIMARY
    status: ResidentStatus = ResidentStatus.PROSPECT
    lease_id: UUID | None = None
    unit_id: UUID | None = None
    move_in_date: date | None = None
    move_out_date: date | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None


class ResidentUpdate(BaseModel):
    email: str | None = None
    phone: str | None = None
    status: ResidentStatus | None = None
    lease_id: UUID | None = None
    unit_id: UUID | None = None
    move_in_date: date | None = None
    move_out_date: date | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
