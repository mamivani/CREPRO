"""HTTP routes for the reporting service."""

from crepro_common import build_crud_router
from crepro_reporting.models import ReportDefinition
from crepro_reporting.repository import report_definitions
from crepro_reporting.schemas import ReportDefinitionCreate, ReportDefinitionUpdate
from fastapi import APIRouter

router = APIRouter()

router.include_router(
    build_crud_router(
        prefix="/api/v1/report-definitions",
        tags=["report-definitions"],
        repository=report_definitions,
        entity_cls=ReportDefinition,
        create_schema=ReportDefinitionCreate,
        update_schema=ReportDefinitionUpdate,
        not_found_detail="Report definition not found",
    )
)
