"""Domain entities for the reporting service: saved report definitions.

Heavy aggregation across other services' data is out of scope for this scaffold; this
service owns the catalog of report definitions that a future query engine will execute.
"""

from enum import StrEnum

from crepro_common import TenantScopedEntity


class ReportCategory(StrEnum):
    OCCUPANCY = "occupancy"
    FINANCIAL = "financial"
    MAINTENANCE = "maintenance"
    OPERATIONS = "operations"


class ReportDefinition(TenantScopedEntity):
    """A named, saved report that can be run on demand or on a schedule."""

    name: str
    category: ReportCategory
    description: str | None = None
    query_reference: str | None = None
