"""HTTP routes for the maintenance service."""

from crepro_common import build_crud_router
from crepro_maintenance.models import (
    ChecklistArea,
    DailyChecklist,
    InventoryCheckout,
    InventorySet,
    MaintenanceRequest,
    MaterialUsage,
    OutsourcedStaff,
    ShiftAttendance,
    StaffShift,
)
from crepro_maintenance.repository import (
    checklist_areas,
    daily_checklists,
    inventory_checkouts,
    inventory_sets,
    material_usages,
    outsourced_staff,
    requests,
    shift_attendance,
    staff_shifts,
)
from crepro_maintenance.schemas import (
    ChecklistAreaCreate,
    ChecklistAreaUpdate,
    DailyChecklistCreate,
    DailyChecklistUpdate,
    InventoryCheckoutCreate,
    InventoryCheckoutUpdate,
    InventorySetCreate,
    InventorySetUpdate,
    MaintenanceRequestCreate,
    MaintenanceRequestUpdate,
    MaterialUsageCreate,
    MaterialUsageUpdate,
    OutsourcedStaffCreate,
    OutsourcedStaffUpdate,
    ShiftAttendanceCreate,
    ShiftAttendanceUpdate,
    StaffShiftCreate,
    StaffShiftUpdate,
)
from fastapi import APIRouter

router = APIRouter()

_resources = [
    (
        "/api/v1/maintenance-requests",
        "maintenance-requests",
        requests,
        MaintenanceRequest,
        MaintenanceRequestCreate,
        MaintenanceRequestUpdate,
        "Maintenance request not found",
    ),
    (
        "/api/v1/material-usages",
        "material-usages",
        material_usages,
        MaterialUsage,
        MaterialUsageCreate,
        MaterialUsageUpdate,
        "Material usage not found",
    ),
    (
        "/api/v1/checklist-areas",
        "checklist-areas",
        checklist_areas,
        ChecklistArea,
        ChecklistAreaCreate,
        ChecklistAreaUpdate,
        "Checklist area not found",
    ),
    (
        "/api/v1/daily-checklists",
        "daily-checklists",
        daily_checklists,
        DailyChecklist,
        DailyChecklistCreate,
        DailyChecklistUpdate,
        "Daily checklist not found",
    ),
    (
        "/api/v1/inventory-sets",
        "inventory-sets",
        inventory_sets,
        InventorySet,
        InventorySetCreate,
        InventorySetUpdate,
        "Inventory set not found",
    ),
    (
        "/api/v1/inventory-checkouts",
        "inventory-checkouts",
        inventory_checkouts,
        InventoryCheckout,
        InventoryCheckoutCreate,
        InventoryCheckoutUpdate,
        "Inventory checkout not found",
    ),
    (
        "/api/v1/outsourced-staff",
        "outsourced-staff",
        outsourced_staff,
        OutsourcedStaff,
        OutsourcedStaffCreate,
        OutsourcedStaffUpdate,
        "Outsourced staff member not found",
    ),
    (
        "/api/v1/staff-shifts",
        "staff-shifts",
        staff_shifts,
        StaffShift,
        StaffShiftCreate,
        StaffShiftUpdate,
        "Staff shift not found",
    ),
    (
        "/api/v1/shift-attendance",
        "shift-attendance",
        shift_attendance,
        ShiftAttendance,
        ShiftAttendanceCreate,
        ShiftAttendanceUpdate,
        "Shift attendance not found",
    ),
]

for prefix, tag, repository, entity_cls, create_schema, update_schema, not_found_detail in _resources:
    router.include_router(
        build_crud_router(
            prefix=prefix,
            tags=[tag],
            repository=repository,
            entity_cls=entity_cls,
            create_schema=create_schema,
            update_schema=update_schema,
            not_found_detail=not_found_detail,
        )
    )
