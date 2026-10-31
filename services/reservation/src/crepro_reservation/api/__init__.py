"""HTTP routes for the reservation service."""

from crepro_common import build_crud_router
from crepro_reservation.models import Reservation
from crepro_reservation.repository import reservations
from crepro_reservation.schemas import ReservationCreate, ReservationUpdate
from fastapi import APIRouter

router = APIRouter()

router.include_router(
    build_crud_router(
        prefix="/api/v1/reservations",
        tags=["reservations"],
        repository=reservations,
        entity_cls=Reservation,
        create_schema=ReservationCreate,
        update_schema=ReservationUpdate,
        not_found_detail="Reservation not found",
    )
)
