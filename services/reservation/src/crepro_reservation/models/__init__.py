"""Domain entities for the reservation service: short-term and pre-lease bookings of a unit.

No reservation module exists in the analyzed sample source; property management there is
lease-only. This is a forward-looking model (short-term/RV-site style bookings), kept
deliberately small until real requirements arrive.
"""

from datetime import date
from enum import StrEnum
from uuid import UUID

from crepro_common import TenantScopedEntity


class ReservationStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"


class ReservationChannel(StrEnum):
    DIRECT = "direct"
    THIRD_PARTY = "third_party"


class Reservation(TenantScopedEntity):
    """A booking of a unit for a bounded date range, outside the standard lease flow."""

    unit_id: UUID
    guest_name: str
    guest_email: str | None = None
    start_date: date
    end_date: date
    status: ReservationStatus = ReservationStatus.PENDING
    channel: ReservationChannel = ReservationChannel.DIRECT
    nightly_rate: float
    total_amount: float = 0
    notes: str | None = None
