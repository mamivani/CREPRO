"""Tenant-scoped in-memory stores for the maintenance service, ahead of a real database."""

from crepro_common import InMemoryRepository
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

requests: InMemoryRepository[MaintenanceRequest] = InMemoryRepository()
material_usages: InMemoryRepository[MaterialUsage] = InMemoryRepository()
checklist_areas: InMemoryRepository[ChecklistArea] = InMemoryRepository()
daily_checklists: InMemoryRepository[DailyChecklist] = InMemoryRepository()
inventory_sets: InMemoryRepository[InventorySet] = InMemoryRepository()
inventory_checkouts: InMemoryRepository[InventoryCheckout] = InMemoryRepository()
outsourced_staff: InMemoryRepository[OutsourcedStaff] = InMemoryRepository()
staff_shifts: InMemoryRepository[StaffShift] = InMemoryRepository()
shift_attendance: InMemoryRepository[ShiftAttendance] = InMemoryRepository()
