"""API request/response DTOs for the property service."""

from uuid import UUID

from crepro_property.models import PropertyStatus, UnitFacing
from pydantic import BaseModel, Field


class PropertyCreate(BaseModel):
    name: str
    parent_property_id: UUID | None = None
    address_line1: str
    address_line2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str
    property_type: str
    status: PropertyStatus = PropertyStatus.AVAILABLE
    description: str | None = None
    max_active_leases: int = 1
    amenities: list[str] = Field(default_factory=list)


class PropertyUpdate(BaseModel):
    name: str | None = None
    parent_property_id: UUID | None = None
    status: PropertyStatus | None = None
    description: str | None = None
    max_active_leases: int | None = None
    amenities: list[str] | None = None


class UnitCreate(BaseModel):
    property_id: UUID
    unit_number: str
    unit_type: str
    bedrooms: int = 0
    bathrooms: int = 0
    builtup_area_sqft: float | None = None
    carpet_area_sqft: float | None = None
    facing: UnitFacing | None = None
    parking_spaces: int = 0
    rent_amount: float
    security_deposit_amount: float = 0
    currency: str = "USD"
    is_smoking_allowed: bool = False
    is_furnished: bool = False
    status: PropertyStatus = PropertyStatus.AVAILABLE
    amenities: list[str] = Field(default_factory=list)


class UnitUpdate(BaseModel):
    rent_amount: float | None = None
    security_deposit_amount: float | None = None
    status: PropertyStatus | None = None
    is_smoking_allowed: bool | None = None
    is_furnished: bool | None = None
    amenities: list[str] | None = None
