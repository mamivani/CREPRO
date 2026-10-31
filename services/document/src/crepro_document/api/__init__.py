"""HTTP routes for the document service."""

from crepro_common import build_crud_router
from crepro_document.models import Document, InsurancePolicy
from crepro_document.repository import documents, insurance_policies
from crepro_document.schemas import (
    DocumentCreate,
    DocumentUpdate,
    InsurancePolicyCreate,
    InsurancePolicyUpdate,
)
from fastapi import APIRouter

router = APIRouter()

router.include_router(
    build_crud_router(
        prefix="/api/v1/documents",
        tags=["documents"],
        repository=documents,
        entity_cls=Document,
        create_schema=DocumentCreate,
        update_schema=DocumentUpdate,
        not_found_detail="Document not found",
    )
)

router.include_router(
    build_crud_router(
        prefix="/api/v1/insurance-policies",
        tags=["insurance-policies"],
        repository=insurance_policies,
        entity_cls=InsurancePolicy,
        create_schema=InsurancePolicyCreate,
        update_schema=InsurancePolicyUpdate,
        not_found_detail="Insurance policy not found",
    )
)
