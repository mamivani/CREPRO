"""API request/response DTOs for the maintenance service."""

from datetime import date, datetime
from uuid import UUID

from crepro_maintenance.models import (
    AttendanceEntry,
    ChecklistItemResult,
    ChecklistShift,
    InventoryKind,
    InventorySetStatus,
    MaterialBillingStatus,
    RequestPriority,
    RequestStatus,
    StaffCategory,
)
from pydantic import BaseModel, Field


class MaintenanceRequestCreate(BaseModel):
    property_id: UUID
    unit_id: UUID | None = None
    title: str
    description: str | None = None
    priority: RequestPriority = RequestPriority.MEDIUM
    reported_by: str | None = None


class MaintenanceRequestUpdate(BaseModel):
    status: RequestStatus | None = None
    priority: RequestPriority | None = None
    assigned_to: str | None = None
    resolved_at: datetime | None = None


class MaterialUsageCreate(BaseModel):
    request_id: UUID
    item_code: str
    description: str | None = None
    quantity: float
    uom: str = "unit"
    rate: float = 0
    amount: float = 0
    billing_status: MaterialBillingStatus = MaterialBillingStatus.REQUESTED


class MaterialUsageUpdate(BaseModel):
    billing_status: MaterialBillingStatus | None = None
    invoiced: bool | None = None


class ChecklistAreaCreate(BaseModel):
    name: str
    tasks: list[str] = Field(default_factory=list)


class ChecklistAreaUpdate(BaseModel):
    tasks: list[str] | None = None


class DailyChecklistCreate(BaseModel):
    property_id: UUID
    checkup_date: date
    shift: ChecklistShift
    area_id: UUID
    items: list[ChecklistItemResult] = Field(default_factory=list)


class DailyChecklistUpdate(BaseModel):
    items: list[ChecklistItemResult] | None = None


class InventorySetCreate(BaseModel):
    kind: InventoryKind
    name: str
    location: str | None = None
    item_count: int = 0


class InventorySetUpdate(BaseModel):
    status: InventorySetStatus | None = None
    item_count: int | None = None


class InventoryCheckoutCreate(BaseModel):
    inventory_set_id: UUID
    staff_category: StaffCategory = StaffCategory.OTHER
    checked_out_to: str
    reason: str


class InventoryCheckoutUpdate(BaseModel):
    returned_at: datetime | None = None


class OutsourcedStaffCreate(BaseModel):
    full_name: str
    id_number: str | None = None
    category: StaffCategory = StaffCategory.OTHER


class OutsourcedStaffUpdate(BaseModel):
    is_active: bool | None = None


class StaffShiftCreate(BaseModel):
    name: str
    category: StaffCategory = StaffCategory.OTHER
    locations: list[str] = Field(default_factory=list)


class StaffShiftUpdate(BaseModel):
    locations: list[str] | None = None


class ShiftAttendanceCreate(BaseModel):
    shift_id: UUID
    shift_date: date
    entries: list[AttendanceEntry] = Field(default_factory=list)


class ShiftAttendanceUpdate(BaseModel):
    entries: list[AttendanceEntry] | None = None
