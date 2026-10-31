"""Domain entities for the utility service: meters and their readings."""

from datetime import date
from enum import StrEnum
from uuid import UUID

from crepro_common import TenantScopedEntity
from pydantic import computed_field


class UtilityType(StrEnum):
    ELECTRICITY = "electricity"
    WATER = "water"
    GAS = "gas"
    HEAT = "heat"
    OTHER = "other"


class MeterStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Meter(TenantScopedEntity):
    """A physical utility meter installed at a unit."""

    unit_id: UUID
    meter_number: str
    utility_type: UtilityType
    status: MeterStatus = MeterStatus.ACTIVE
    initial_reading: float = 0
    installation_date: date | None = None
    deactivation_date: date | None = None


class MeterReading(TenantScopedEntity):
    """A single recorded reading for a meter, used to compute and bill consumption."""

    meter_id: UUID
    reading_date: date
    previous_reading: float
    current_reading: float
    billable: bool = True
    erp_invoice_reference: str | None = None

    @computed_field
    @property
    def consumption(self) -> float:
        return self.current_reading - self.previous_reading
