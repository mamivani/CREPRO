"""Domain entities for the lease service: lease contracts, charges, increments, and exits."""

from datetime import date
from enum import StrEnum
from uuid import UUID

from crepro_common import TenantScopedEntity


class LeaseFrequency(StrEnum):
    MONTHLY = "monthly"
    BI_MONTHLY = "bi_monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUALLY = "semi_annually"
    ANNUALLY = "annually"


class LeaseStatus(StrEnum):
    DRAFT = "draft"
    UPCOMING = "upcoming"
    ACTIVE = "active"
    EXPIRED = "expired"
    CLOSED = "closed"
    RENEWAL = "renewal"
    VACATING = "vacating"
    TERMINATED = "terminated"


class ChargeBasis(StrEnum):
    FIXED = "fixed"
    BUILTUP_AREA = "builtup_area"
    CARPET_AREA = "carpet_area"


class IncrementUnit(StrEnum):
    MONTH = "month"
    YEAR = "year"


class IncrementType(StrEnum):
    PERCENT = "percent"
    AMOUNT = "amount"


class SecurityDepositStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    INVOICE_RAISED = "invoice_raised"
    RECEIVED = "received"
    RECEIVED_IN_PART = "received_in_part"
    RETURNED_IN_PART = "returned_in_part"
    RETURNED = "returned"
    RECOVERED_FOR_RENT = "recovered_for_rent"
    RECOVERED_FOR_REPAIRS = "recovered_for_repairs"


class ExitType(StrEnum):
    EXPIRY = "expiry"
    PRE_MATURE = "pre_mature"
    TERMINATION = "termination"


class ResidentType(StrEnum):
    PRIMARY = "primary"
    CO_RESIDENT = "co_resident"
    GUARANTOR = "guarantor"
    APPLICANT = "applicant"


class ResidentStatus(StrEnum):
    PROSPECT = "prospect"
    ACTIVE = "active"
    FORMER = "former"


class Lease(TenantScopedEntity):
    """A tenancy contract for one resident on one unit."""

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
    amended_from_id: UUID | None = None


class LeaseCharge(TenantScopedEntity):
    """A recurring billable line on a lease, e.g. rent or a maintenance fee."""

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


class LeaseIncrementRule(TenantScopedEntity):
    """A scheduled rent increase applied to a lease charge."""

    lease_id: UUID
    charge_code: str
    increment_every: int
    increment_unit: IncrementUnit
    increment_type: IncrementType
    increment_value: float
    effective_from: date
    is_active: bool = True


class LeaseInvoiceScheduleEntry(TenantScopedEntity):
    """One planned invoice line, produced ahead of time so billing can run unattended."""

    lease_id: UUID
    charge_id: UUID
    date_to_invoice: date
    quantity: float = 1
    rate: float
    currency: str = "USD"
    tax_percent: float = 0
    invoiced: bool = False
    erp_invoice_reference: str | None = None


class LeaseExit(TenantScopedEntity):
    """A move-out event, whether by natural expiry, early exit, or termination."""

    lease_id: UUID
    exit_type: ExitType
    effective_date: date
    details: str | None = None


class Resident(TenantScopedEntity):
    """A person associated with a lease: a renter, co-renter, guarantor, or applicant.

    Distinct from the external ERP's customer record, which the ERP adapter maintains
    separately for billing; this entity is the platform's own source of truth for who
    lives where.
    """

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
