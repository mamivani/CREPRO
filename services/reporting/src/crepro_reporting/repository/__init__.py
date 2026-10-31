"""Tenant-scoped in-memory store for the reporting service, ahead of a real database."""

from crepro_common import InMemoryRepository
from crepro_reporting.models import ReportDefinition

report_definitions: InMemoryRepository[ReportDefinition] = InMemoryRepository()
