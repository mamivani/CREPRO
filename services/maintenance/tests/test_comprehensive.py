"""Comprehensive tests for maintenance service: work requests, staff, and inventory."""

import pytest
from uuid import uuid4, UUID
from datetime import date, datetime

from crepro_maintenance.main import app
from crepro_maintenance.models import (
    MaintenanceRequest, MaterialUsage, OutsourcedStaff, StaffShift,
    RequestStatus, RequestPriority, MaterialBillingStatus, StaffCategory
)
from crepro_maintenance.repository import (
    requests, material_usages, outsourced_staff, staff_shifts
)
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_repositories():
    """Reset in-memory repositories before each test."""
    requests._rows.clear()
    material_usages._rows.clear()
    outsourced_staff._rows.clear()
    staff_shifts._rows.clear()
    yield
    requests._rows.clear()
    material_usages._rows.clear()
    outsourced_staff._rows.clear()
    staff_shifts._rows.clear()


def _headers(tenant_id: UUID | None = None) -> dict[str, str]:
    """Generate request headers with tenant context."""
    if tenant_id is None:
        tenant_id = uuid4()
    return {"X-Tenant-Id": str(tenant_id)}


class TestMaintenanceRequestCRUD:
    """Test MaintenanceRequest CRUD operations."""

    def test_create_request_minimal(self):
        """Create a request with required fields only."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/maintenance-requests",
            json={
                "property_id": str(uuid4()),
                "title": "Broken AC",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Broken AC"
        assert data["status"] == "open"
        assert data["priority"] == "medium"

    def test_create_request_with_all_fields(self):
        """Create a request with all optional fields."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/maintenance-requests",
            json={
                "property_id": str(uuid4()),
                "unit_id": str(uuid4()),
                "title": "Roof leak",
                "description": "Water dripping from bedroom ceiling",
                "priority": "high",
                "reported_by": "tenant@example.com",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Water dripping from bedroom ceiling"
        assert data["priority"] == "high"
        assert data["reported_by"] == "tenant@example.com"

    def test_get_request(self):
        """Retrieve a request."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        create_response = client.post(
            "/api/v1/maintenance-requests",
            json={
                "property_id": str(uuid4()),
                "title": "Fix door",
            },
            headers=headers,
        )
        
        request_id = create_response.json()["id"]
        
        get_response = client.get(f"/api/v1/maintenance-requests/{request_id}", headers=headers)
        
        assert get_response.status_code == 200
        assert get_response.json()["id"] == request_id

    def test_update_request(self):
        """Update a request."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        create_response = client.post(
            "/api/v1/maintenance-requests",
            json={
                "property_id": str(uuid4()),
                "title": "Fix door",
            },
            headers=headers,
        )
        
        request_id = create_response.json()["id"]
        
        update_response = client.patch(
            f"/api/v1/maintenance-requests/{request_id}",
            json={"status": "completed", "priority": "high"},
            headers=headers,
        )
        
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "completed"
        assert update_response.json()["priority"] == "high"

    def test_delete_request(self):
        """Delete a request."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        create_response = client.post(
            "/api/v1/maintenance-requests",
            json={
                "property_id": str(uuid4()),
                "title": "Fix door",
            },
            headers=headers,
        )
        
        request_id = create_response.json()["id"]
        
        delete_response = client.delete(
            f"/api/v1/maintenance-requests/{request_id}",
            headers=headers,
        )
        
        assert delete_response.status_code == 204
        
        get_response = client.get(f"/api/v1/maintenance-requests/{request_id}", headers=headers)
        assert get_response.status_code == 404

    def test_list_requests(self):
        """List requests for a tenant."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        for i in range(3):
            client.post(
                "/api/v1/maintenance-requests",
                json={
                    "property_id": str(uuid4()),
                    "title": f"Issue {i}",
                },
                headers=headers,
            )
        
        list_response = client.get("/api/v1/maintenance-requests", headers=headers)
        
        assert list_response.status_code == 200
        assert len(list_response.json()) == 3


class TestMaterialUsageCRUD:
    """Test MaterialUsage CRUD operations."""

    def test_create_material_minimal(self):
        """Create a material usage with required fields."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/material-usages",
            json={
                "request_id": str(uuid4()),
                "item_code": "PAINT-001",
                "quantity": 2,
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["item_code"] == "PAINT-001"
        assert data["quantity"] == 2
        assert data["billing_status"] == "requested"

    def test_create_material_full(self):
        """Create a material usage with all fields."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/material-usages",
            json={
                "request_id": str(uuid4()),
                "item_code": "PAINT-002",
                "description": "Interior paint",
                "quantity": 5,
                "uom": "gallon",
                "rate": 50,
                "amount": 250,
                "billing_status": "bill",
                "invoiced": True,
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Interior paint"
        assert data["amount"] == 250

    def test_list_materials(self):
        """List material usages."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        for i in range(2):
            client.post(
                "/api/v1/material-usages",
                json={
                    "request_id": str(uuid4()),
                    "item_code": f"ITEM-{i}",
                    "quantity": 1,
                },
                headers=headers,
            )
        
        list_response = client.get("/api/v1/material-usages", headers=headers)
        
        assert list_response.status_code == 200
        assert len(list_response.json()) == 2


class TestOutsourcedStaffCRUD:
    """Test OutsourcedStaff CRUD operations."""

    def test_create_staff_minimal(self):
        """Create an outsourced staff member."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/outsourced-staff",
            json={
                "full_name": "John Cleaner",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["full_name"] == "John Cleaner"
        assert data["category"] == "other"
        assert data["is_active"] == True

    def test_create_staff_with_fields(self):
        """Create a staff member with all fields."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/outsourced-staff",
            json={
                "full_name": "Jane Security",
                "id_number": "SEC-001",
                "category": "security",
                "is_active": True,
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201
        assert response.json()["category"] == "security"

    def test_list_staff(self):
        """List staff members."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        for i in range(2):
            client.post(
                "/api/v1/outsourced-staff",
                json={
                    "full_name": f"Staff {i}",
                },
                headers=headers,
            )
        
        list_response = client.get("/api/v1/outsourced-staff", headers=headers)
        
        assert list_response.status_code == 200
        assert len(list_response.json()) == 2


class TestStaffShiftCRUD:
    """Test StaffShift CRUD operations."""

    def test_create_shift_minimal(self):
        """Create a staff shift."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/staff-shifts",
            json={
                "name": "Night Security",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Night Security"
        assert data["category"] == "other"

    def test_create_shift_full(self):
        """Create a shift with all fields."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/staff-shifts",
            json={
                "name": "Day Cleaning",
                "category": "cleaning",
                "locations": ["Main Building", "Parking Lot"],
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["category"] == "cleaning"
        assert len(data["locations"]) == 2


class TestMaintenanceCrossTenantIsolation:
    """Test tenant isolation for maintenance entities."""

    def test_request_isolation_read(self):
        """Verify Tenant B cannot read Tenant A's request."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        create_response = client.post(
            "/api/v1/maintenance-requests",
            json={
                "property_id": str(uuid4()),
                "title": "Secret repair",
            },
            headers=_headers(tenant_a),
        )
        
        request_id = create_response.json()["id"]
        
        get_response = client.get(
            f"/api/v1/maintenance-requests/{request_id}",
            headers=_headers(tenant_b),
        )
        
        assert get_response.status_code == 404

    def test_request_isolation_list(self):
        """Verify list returns only tenant's requests."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        for _ in range(2):
            client.post(
                "/api/v1/maintenance-requests",
                json={
                    "property_id": str(uuid4()),
                    "title": "Request A",
                },
                headers=_headers(tenant_a),
            )
        
        client.post(
            "/api/v1/maintenance-requests",
            json={
                "property_id": str(uuid4()),
                "title": "Request B",
            },
            headers=_headers(tenant_b),
        )
        
        list_a = client.get("/api/v1/maintenance-requests", headers=_headers(tenant_a))
        list_b = client.get("/api/v1/maintenance-requests", headers=_headers(tenant_b))
        
        assert len(list_a.json()) == 2
        assert len(list_b.json()) == 1

    def test_material_isolation_update(self):
        """Verify Tenant B cannot update Tenant A's material."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        create_response = client.post(
            "/api/v1/material-usages",
            json={
                "request_id": str(uuid4()),
                "item_code": "PAINT-001",
                "quantity": 2,
            },
            headers=_headers(tenant_a),
        )
        
        material_id = create_response.json()["id"]
        
        update_response = client.patch(
            f"/api/v1/material-usages/{material_id}",
            json={"quantity": 10},
            headers=_headers(tenant_b),
        )
        
        assert update_response.status_code == 404


class TestMaintenanceSchema:
    """Test maintenance schema validation."""

    def test_request_invalid_status(self):
        """Verify invalid request status is rejected."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        create_response = client.post(
            "/api/v1/maintenance-requests",
            json={
                "property_id": str(uuid4()),
                "title": "Fix",
            },
            headers=headers,
        )
        assert create_response.status_code == 201
        
        request_id = create_response.json()["id"]
        
        response = client.patch(
            f"/api/v1/maintenance-requests/{request_id}",
            json={"status": "invalid"},
            headers=headers,
        )
        
        assert response.status_code >= 400

    def test_request_invalid_priority(self):
        """Verify invalid priority is rejected."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/maintenance-requests",
            json={
                "property_id": str(uuid4()),
                "title": "Fix",
                "priority": "invalid",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code >= 400

    def test_material_invalid_billing_status(self):
        """Verify invalid billing status is rejected."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/material-usages",
            json={
                "request_id": str(uuid4()),
                "item_code": "ITEM-001",
                "quantity": 1,
                "billing_status": "invalid",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code >= 400

    def test_staff_invalid_category(self):
        """Verify invalid staff category is rejected."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/outsourced-staff",
            json={
                "full_name": "Staff",
                "category": "invalid",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code >= 400


class TestMaintenanceEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_request_empty_title(self):
        """Verify empty title is allowed."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/maintenance-requests",
            json={
                "property_id": str(uuid4()),
                "title": "",
            },
            headers=_headers(tenant_id),
        )
        
        # Allow empty title
        assert response.status_code == 201

    def test_material_negative_quantity(self):
        """Verify negative quantity is allowed."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/material-usages",
            json={
                "request_id": str(uuid4()),
                "item_code": "ITEM-001",
                "quantity": -5,
            },
            headers=_headers(tenant_id),
        )
        
        # Allow negative quantities (for reversals/adjustments)
        assert response.status_code == 201

    def test_material_zero_quantity(self):
        """Verify zero quantity is allowed."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/material-usages",
            json={
                "request_id": str(uuid4()),
                "item_code": "ITEM-001",
                "quantity": 0,
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201

    def test_get_nonexistent_request(self):
        """Verify getting nonexistent request returns 404."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.get(
            f"/api/v1/maintenance-requests/{uuid4()}",
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 404

    def test_request_status_enum(self):
        """Verify all request statuses work (via update)."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        for status in ["open", "in_progress", "completed", "cancelled"]:
            # Create request
            create_response = client.post(
                "/api/v1/maintenance-requests",
                json={
                    "property_id": str(uuid4()),
                    "title": "Fix",
                },
                headers=headers,
            )
            assert create_response.status_code == 201
            
            request_id = create_response.json()["id"]
            
            # Update to target status
            response = client.patch(
                f"/api/v1/maintenance-requests/{request_id}",
                json={"status": status},
                headers=headers,
            )
            assert response.status_code == 200
            assert response.json()["status"] == status

    def test_request_priority_enum(self):
        """Verify all request priorities work."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        for priority in ["low", "medium", "high", "urgent"]:
            response = client.post(
                "/api/v1/maintenance-requests",
                json={
                    "property_id": str(uuid4()),
                    "title": "Fix",
                    "priority": priority,
                },
                headers=_headers(tenant_id),
            )
            assert response.status_code == 201
            assert response.json()["priority"] == priority

    def test_staff_category_enum(self):
        """Verify all staff categories work."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        for category in ["cleaning", "security", "landscaping", "other"]:
            response = client.post(
                "/api/v1/outsourced-staff",
                json={
                    "full_name": "Staff",
                    "category": category,
                },
                headers=_headers(tenant_id),
            )
            assert response.status_code == 201
            assert response.json()["category"] == category
