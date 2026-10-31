"""API request/response DTOs for the reservation service."""

from datetime import date
from uuid import UUID

from crepro_reservation.models import ReservationChannel, ReservationStatus
from pydantic import BaseModel


class ReservationCreate(BaseModel):
    unit_id: UUID
    guest_name: str
    guest_email: str | None = None
    start_date: date
    end_date: date
    channel: ReservationChannel = ReservationChannel.DIRECT
    nightly_rate: float
    notes: str | None = None


class ReservationUpdate(BaseModel):
    status: ReservationStatus | None = None
    notes: str | None = None
