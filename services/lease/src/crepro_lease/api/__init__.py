"""HTTP routes for the lease service."""

from crepro_common import build_crud_router
from crepro_lease.models import Lease, LeaseCharge, LeaseExit, LeaseIncrementRule, Resident
from crepro_lease.repository import charges, exits, increment_rules, leases, residents
from crepro_lease.schemas import (
    LeaseChargeCreate,
    LeaseChargeUpdate,
    LeaseCreate,
    LeaseExitCreate,
    LeaseExitUpdate,
    LeaseIncrementRuleCreate,
    LeaseIncrementRuleUpdate,
    LeaseUpdate,
    ResidentCreate,
    ResidentUpdate,
)
from fastapi import APIRouter

router = APIRouter()

router.include_router(
    build_crud_router(
        prefix="/api/v1/leases",
        tags=["leases"],
        repository=leases,
        entity_cls=Lease,
        create_schema=LeaseCreate,
        update_schema=LeaseUpdate,
        not_found_detail="Lease not found",
    )
)

router.include_router(
    build_crud_router(
        prefix="/api/v1/lease-charges",
        tags=["lease-charges"],
        repository=charges,
        entity_cls=LeaseCharge,
        create_schema=LeaseChargeCreate,
        update_schema=LeaseChargeUpdate,
        not_found_detail="Lease charge not found",
    )
)

router.include_router(
    build_crud_router(
        prefix="/api/v1/lease-increment-rules",
        tags=["lease-increment-rules"],
        repository=increment_rules,
        entity_cls=LeaseIncrementRule,
        create_schema=LeaseIncrementRuleCreate,
        update_schema=LeaseIncrementRuleUpdate,
        not_found_detail="Lease increment rule not found",
    )
)

router.include_router(
    build_crud_router(
        prefix="/api/v1/lease-exits",
        tags=["lease-exits"],
        repository=exits,
        entity_cls=LeaseExit,
        create_schema=LeaseExitCreate,
        update_schema=LeaseExitUpdate,
        not_found_detail="Lease exit not found",
    )
)

router.include_router(
    build_crud_router(
        prefix="/api/v1/residents",
        tags=["residents"],
        repository=residents,
        entity_cls=Resident,
        create_schema=ResidentCreate,
        update_schema=ResidentUpdate,
        not_found_detail="Resident not found",
    )
)
