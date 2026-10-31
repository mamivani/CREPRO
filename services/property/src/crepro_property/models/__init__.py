"""Domain entities for the property service: portfolio, buildings, units, and amenities."""

from enum import StrEnum
from uuid import UUID

from crepro_common import TenantScopedEntity
from pydantic import Field


class PropertyStatus(StrEnum):
    AVAILABLE = "available"
    BOOKED = "booked"
    ON_LEASE = "on_lease"
    OFF_LEASE_SOON = "off_lease_soon"
    MANAGED_FOR_OWNER = "managed_for_owner"
    ON_SALE = "on_sale"
    SOLD = "sold"
    VACATING = "vacating"
    RENOVATION = "renovation"
    REMOVED = "removed"


class UnitFacing(StrEnum):
    NORTH = "north"
    NORTH_EAST = "north_east"
    EAST = "east"
    SOUTH_EAST = "south_east"
    SOUTH = "south"
    SOUTH_WEST = "south_west"
    WEST = "west"
    NORTH_WEST = "north_west"


class Property(TenantScopedEntity):
    """A building, community, or standalone real-estate asset. May nest under a parent property."""

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


class Unit(TenantScopedEntity):
    """A single leasable unit belonging to a property."""

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
