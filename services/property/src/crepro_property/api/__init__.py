"""HTTP routes for the property service."""

from crepro_common import build_crud_router
from crepro_property.models import Property, Unit
from crepro_property.repository import outbox, properties, units
from crepro_property.schemas import PropertyCreate, PropertyUpdate, UnitCreate, UnitUpdate
from fastapi import APIRouter

router = APIRouter()

router.include_router(
    build_crud_router(
        prefix="/api/v1/properties",
        tags=["properties"],
        repository=properties,
        entity_cls=Property,
        create_schema=PropertyCreate,
        update_schema=PropertyUpdate,
        not_found_detail="Property not found",
        # Erp adapter's doctype_map already routes "PropertyCreated" to the
        # external ERP's Property doctype (services/erp_adapter/.../push.py).
        outbox=outbox,
        outbox_event_type="PropertyCreated",
        outbox_source="property",
    )
)

router.include_router(
    build_crud_router(
        prefix="/api/v1/units",
        tags=["units"],
        repository=units,
        entity_cls=Unit,
        create_schema=UnitCreate,
        update_schema=UnitUpdate,
        not_found_detail="Unit not found",
    )
)
