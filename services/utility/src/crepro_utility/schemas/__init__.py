"""API request/response DTOs for the utility service."""

from datetime import date
from uuid import UUID

from crepro_utility.models import MeterStatus, UtilityType
from pydantic import BaseModel


class MeterCreate(BaseModel):
    unit_id: UUID
    meter_number: str
    utility_type: UtilityType
    initial_reading: float = 0
    installation_date: date | None = None


class MeterUpdate(BaseModel):
    status: MeterStatus | None = None
    deactivation_date: date | None = None


class MeterReadingCreate(BaseModel):
    meter_id: UUID
    reading_date: date
    previous_reading: float
    current_reading: float
    billable: bool = True


class MeterReadingUpdate(BaseModel):
    billable: bool | None = None
    erp_invoice_reference: str | None = None
