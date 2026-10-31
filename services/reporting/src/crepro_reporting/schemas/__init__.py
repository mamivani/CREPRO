"""API request/response DTOs for the reporting service."""

from crepro_reporting.models import ReportCategory
from pydantic import BaseModel


class ReportDefinitionCreate(BaseModel):
    name: str
    category: ReportCategory
    description: str | None = None
    query_reference: str | None = None


class ReportDefinitionUpdate(BaseModel):
    description: str | None = None
    query_reference: str | None = None
