"""HTTP routes for the utility service."""

from crepro_common import build_crud_router
from crepro_utility.models import Meter, MeterReading
from crepro_utility.repository import meters, readings
from crepro_utility.schemas import MeterCreate, MeterReadingCreate, MeterReadingUpdate, MeterUpdate
from fastapi import APIRouter

router = APIRouter()

router.include_router(
    build_crud_router(
        prefix="/api/v1/meters",
        tags=["meters"],
        repository=meters,
        entity_cls=Meter,
        create_schema=MeterCreate,
        update_schema=MeterUpdate,
        not_found_detail="Meter not found",
    )
)

router.include_router(
    build_crud_router(
        prefix="/api/v1/meter-readings",
        tags=["meter-readings"],
        repository=readings,
        entity_cls=MeterReading,
        create_schema=MeterReadingCreate,
        update_schema=MeterReadingUpdate,
        not_found_detail="Meter reading not found",
    )
)
