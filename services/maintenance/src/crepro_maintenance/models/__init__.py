"""Domain entities for the maintenance service: work requests, checklists, and facility operations."""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from crepro_common import TenantScopedEntity
from pydantic import BaseModel, Field


class RequestStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RequestPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MaterialBillingStatus(StrEnum):
    REQUESTED = "requested"
    RECEIVED_WIP = "received_wip"
    WORK_DONE = "work_done"
    BILL = "bill"
    SELF_CONSUMPTION = "self_consumption"


class ChecklistShift(StrEnum):
    DAY = "day"
    NIGHT = "night"


class InventoryKind(StrEnum):
    KEY = "key"
    TOOL = "tool"


class InventorySetStatus(StrEnum):
    IN = "in"
    OUT = "out"
    LOST = "lost"


class StaffCategory(StrEnum):
    CLEANING = "cleaning"
    SECURITY = "security"
    LANDSCAPING = "landscaping"
    OTHER = "other"


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    DAY_OFF = "day_off"


class MaintenanceRequest(TenantScopedEntity):
    """A work order raised against a property or unit."""

    property_id: UUID
    unit_id: UUID | None = None
    title: str
    description: str | None = None
    status: RequestStatus = RequestStatus.OPEN
    priority: RequestPriority = RequestPriority.MEDIUM
    reported_by: str | None = None
    assigned_to: str | None = None
    resolved_at: datetime | None = None


class MaterialUsage(TenantScopedEntity):
    """A material consumed while working a maintenance request, pending billing."""

    request_id: UUID
    item_code: str
    description: str | None = None
    quantity: float
    uom: str = "unit"
    rate: float = 0
    amount: float = 0
    billing_status: MaterialBillingStatus = MaterialBillingStatus.REQUESTED
    invoiced: bool = False


class ChecklistItemResult(BaseModel):
    task_name: str
    remarks: str | None = None
    photo_url: str | None = None
    linked_request_id: UUID | None = None


class ChecklistArea(TenantScopedEntity):
    """A physical area with a standard set of inspection tasks, e.g. lobby or parking garage."""

    name: str
    tasks: list[str] = Field(default_factory=list)


class DailyChecklist(TenantScopedEntity):
    """One completed walk-through of a checklist area on a given shift."""

    property_id: UUID
    checkup_date: date
    shift: ChecklistShift
    area_id: UUID
    items: list[ChecklistItemResult] = Field(default_factory=list)


class InventorySet(TenantScopedEntity):
    """A tracked set of physical keys or tools kept at a shared location, checked out as a unit."""

    kind: InventoryKind
    name: str
    location: str | None = None
    item_count: int = 0
    status: InventorySetStatus = InventorySetStatus.IN


class InventoryCheckout(TenantScopedEntity):
    """A single checkout/return cycle for an inventory set."""

    inventory_set_id: UUID
    staff_category: StaffCategory = StaffCategory.OTHER
    checked_out_to: str
    reason: str
    checked_out_at: datetime = Field(default_factory=datetime.now)
    returned_at: datetime | None = None


class OutsourcedStaff(TenantScopedEntity):
    """A worker employed through a staffing vendor rather than directly, e.g. cleaning or security."""

    full_name: str
    id_number: str | None = None
    category: StaffCategory = StaffCategory.OTHER
    is_active: bool = True


class StaffShift(TenantScopedEntity):
    """A named shift pattern for outsourced staff, with the locations it covers."""

    name: str
    category: StaffCategory = StaffCategory.OTHER
    locations: list[str] = Field(default_factory=list)


class AttendanceEntry(BaseModel):
    person_name: str
    position: str | None = None
    status: AttendanceStatus = AttendanceStatus.PRESENT
    remarks: str | None = None


class ShiftAttendance(TenantScopedEntity):
    """Attendance taken for a shift on a given date."""

    shift_id: UUID
    shift_date: date
    entries: list[AttendanceEntry] = Field(default_factory=list)
