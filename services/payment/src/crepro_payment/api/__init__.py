"""HTTP routes for the payment service."""

from crepro_common import build_crud_router
from crepro_payment.models import PaymentRecord, SecurityDeposit
from crepro_payment.repository import payments, security_deposits
from crepro_payment.schemas import (
    PaymentRecordCreate,
    PaymentRecordUpdate,
    SecurityDepositCreate,
    SecurityDepositUpdate,
)
from fastapi import APIRouter

router = APIRouter()

router.include_router(
    build_crud_router(
        prefix="/api/v1/payments",
        tags=["payments"],
        repository=payments,
        entity_cls=PaymentRecord,
        create_schema=PaymentRecordCreate,
        update_schema=PaymentRecordUpdate,
        not_found_detail="Payment not found",
    )
)

router.include_router(
    build_crud_router(
        prefix="/api/v1/security-deposits",
        tags=["security-deposits"],
        repository=security_deposits,
        entity_cls=SecurityDeposit,
        create_schema=SecurityDepositCreate,
        update_schema=SecurityDepositUpdate,
        not_found_detail="Security deposit not found",
    )
)
