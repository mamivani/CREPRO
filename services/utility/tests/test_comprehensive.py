"""Comprehensive tests for utility service: meters and readings."""

from uuid import UUID, uuid4

import pytest
from crepro_utility.main import app
from crepro_utility.repository import meters, readings
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_repositories():
    """Reset in-memory repositories before each test."""
    meters._rows.clear()
    readings._rows.clear()
    yield
    meters._rows.clear()
    readings._rows.clear()


def _headers(tenant_id: UUID | None = None) -> dict[str, str]:
    """Generate request headers with tenant context."""
    if tenant_id is None:
        tenant_id = uuid4()
    return {"X-Tenant-Id": str(tenant_id)}


class TestMeterCRUD:
    """Test Meter CRUD operations."""

    def test_create_meter_minimal(self):
        """Create a meter with required fields only."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/meters",
            json={
                "unit_id": str(uuid4()),
                "meter_number": "MTR-001",
                "utility_type": "electricity",
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["meter_number"] == "MTR-001"
        assert data["utility_type"] == "electricity"
        assert data["status"] == "active"
        assert data["initial_reading"] == 0

    def test_create_meter_with_all_fields(self):
        """Create a meter with all optional fields."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/meters",
            json={
                "unit_id": str(uuid4()),
                "meter_number": "WATER-001",
                "utility_type": "water",
                "initial_reading": 1000,
                "installation_date": "2024-01-01",
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "active"  # Default status
        assert data["initial_reading"] == 1000
        assert data["installation_date"] == "2024-01-01"

    def test_get_meter(self):
        """Retrieve a meter."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        create_response = client.post(
            "/api/v1/meters",
            json={
                "unit_id": str(uuid4()),
                "meter_number": "MTR-002",
                "utility_type": "gas",
            },
            headers=headers,
        )

        meter_id = create_response.json()["id"]

        get_response = client.get(f"/api/v1/meters/{meter_id}", headers=headers)

        assert get_response.status_code == 200
        assert get_response.json()["id"] == meter_id

    def test_update_meter(self):
        """Update a meter."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        create_response = client.post(
            "/api/v1/meters",
            json={
                "unit_id": str(uuid4()),
                "meter_number": "MTR-003",
                "utility_type": "electricity",
            },
            headers=headers,
        )

        meter_id = create_response.json()["id"]

        update_response = client.patch(
            f"/api/v1/meters/{meter_id}",
            json={"status": "inactive", "deactivation_date": "2025-01-01"},
            headers=headers,
        )

        assert update_response.status_code == 200
        assert update_response.json()["status"] == "inactive"
        assert update_response.json()["deactivation_date"] == "2025-01-01"

    def test_list_meters(self):
        """List meters for a tenant."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        for i in range(3):
            client.post(
                "/api/v1/meters",
                json={
                    "unit_id": str(uuid4()),
                    "meter_number": f"MTR-{i}",
                    "utility_type": "electricity",
                },
                headers=headers,
            )

        list_response = client.get("/api/v1/meters", headers=headers)

        assert list_response.status_code == 200
        assert len(list_response.json()) == 3


class TestMeterReadingCRUD:
    """Test MeterReading CRUD operations."""

    def test_create_reading_minimal(self):
        """Create a reading with required fields."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/meter-readings",
            json={
                "meter_id": str(uuid4()),
                "reading_date": "2025-01-15",
                "previous_reading": 1000,
                "current_reading": 1100,
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["reading_date"] == "2025-01-15"
        assert data["previous_reading"] == 1000
        assert data["current_reading"] == 1100
        assert data["billable"]
        assert data["consumption"] == 100

    def test_create_reading_with_optional(self):
        """Create a reading with optional fields."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/meter-readings",
            json={
                "meter_id": str(uuid4()),
                "reading_date": "2025-01-15",
                "previous_reading": 1000,
                "current_reading": 1100,
                "billable": False,
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code == 201
        data = response.json()
        assert not data["billable"]

    def test_get_reading(self):
        """Retrieve a reading."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        create_response = client.post(
            "/api/v1/meter-readings",
            json={
                "meter_id": str(uuid4()),
                "reading_date": "2025-01-15",
                "previous_reading": 1000,
                "current_reading": 1100,
            },
            headers=headers,
        )

        reading_id = create_response.json()["id"]

        get_response = client.get(f"/api/v1/meter-readings/{reading_id}", headers=headers)

        assert get_response.status_code == 200

    def test_update_reading(self):
        """Update a reading."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        create_response = client.post(
            "/api/v1/meter-readings",
            json={
                "meter_id": str(uuid4()),
                "reading_date": "2025-01-15",
                "previous_reading": 1000,
                "current_reading": 1100,
            },
            headers=headers,
        )

        reading_id = create_response.json()["id"]

        update_response = client.patch(
            f"/api/v1/meter-readings/{reading_id}",
            json={"billable": False, "erp_invoice_reference": "ERP-INV-123"},
            headers=headers,
        )

        assert update_response.status_code == 200
        assert not update_response.json()["billable"]
        assert update_response.json()["erp_invoice_reference"] == "ERP-INV-123"

    def test_list_readings(self):
        """List readings for a tenant."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        for i in range(2):
            client.post(
                "/api/v1/meter-readings",
                json={
                    "meter_id": str(uuid4()),
                    "reading_date": "2025-01-15",
                    "previous_reading": 1000 + i * 100,
                    "current_reading": 1100 + i * 100,
                },
                headers=headers,
            )

        list_response = client.get("/api/v1/meter-readings", headers=headers)

        assert list_response.status_code == 200
        assert len(list_response.json()) == 2


class TestUtilityCrossTenantIsolation:
    """Test tenant isolation for utility entities."""

    def test_meter_isolation_read(self):
        """Verify Tenant B cannot read Tenant A's meter."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()

        create_response = client.post(
            "/api/v1/meters",
            json={
                "unit_id": str(uuid4()),
                "meter_number": "SECRET-MTR",
                "utility_type": "electricity",
            },
            headers=_headers(tenant_a),
        )

        meter_id = create_response.json()["id"]

        get_response = client.get(f"/api/v1/meters/{meter_id}", headers=_headers(tenant_b))

        assert get_response.status_code == 404

    def test_meter_isolation_list(self):
        """Verify list returns only tenant's meters."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()

        for _ in range(2):
            client.post(
                "/api/v1/meters",
                json={
                    "unit_id": str(uuid4()),
                    "meter_number": "MTR-A",
                    "utility_type": "electricity",
                },
                headers=_headers(tenant_a),
            )

        client.post(
            "/api/v1/meters",
            json={
                "unit_id": str(uuid4()),
                "meter_number": "MTR-B",
                "utility_type": "water",
            },
            headers=_headers(tenant_b),
        )

        list_a = client.get("/api/v1/meters", headers=_headers(tenant_a))
        list_b = client.get("/api/v1/meters", headers=_headers(tenant_b))

        assert len(list_a.json()) == 2
        assert len(list_b.json()) == 1

    def test_reading_isolation_update(self):
        """Verify Tenant B cannot update Tenant A's reading."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()

        create_response = client.post(
            "/api/v1/meter-readings",
            json={
                "meter_id": str(uuid4()),
                "reading_date": "2025-01-15",
                "previous_reading": 1000,
                "current_reading": 1100,
            },
            headers=_headers(tenant_a),
        )

        reading_id = create_response.json()["id"]

        update_response = client.patch(
            f"/api/v1/meter-readings/{reading_id}",
            json={"billable": False},
            headers=_headers(tenant_b),
        )

        assert update_response.status_code == 404


class TestUtilitySchema:
    """Test utility schema validation."""

    def test_meter_invalid_utility_type(self):
        """Verify invalid utility type is rejected."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/meters",
            json={
                "unit_id": str(uuid4()),
                "meter_number": "MTR-001",
                "utility_type": "invalid",
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code >= 400

    def test_meter_invalid_status(self):
        """Verify invalid meter status is rejected on update."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        create_response = client.post(
            "/api/v1/meters",
            json={
                "unit_id": str(uuid4()),
                "meter_number": "MTR-001",
                "utility_type": "electricity",
            },
            headers=headers,
        )

        meter_id = create_response.json()["id"]

        response = client.patch(
            f"/api/v1/meters/{meter_id}",
            json={"status": "invalid"},
            headers=headers,
        )

        assert response.status_code >= 400

    def test_reading_missing_required_field(self):
        """Verify missing required field is rejected."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/meter-readings",
            json={
                "meter_id": str(uuid4()),
                "reading_date": "2025-01-15",
                "previous_reading": 1000,
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code >= 400


class TestUtilityEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_meter_negative_initial_reading(self):
        """Verify negative initial reading is allowed."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/meters",
            json={
                "unit_id": str(uuid4()),
                "meter_number": "MTR-001",
                "utility_type": "electricity",
                "initial_reading": -100,
            },
            headers=_headers(tenant_id),
        )

        # Allow negative readings
        assert response.status_code == 201

    def test_reading_decreasing_consumption(self):
        """Verify reading where current < previous is allowed (meter reset)."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/meter-readings",
            json={
                "meter_id": str(uuid4()),
                "reading_date": "2025-01-15",
                "previous_reading": 1000,
                "current_reading": 500,
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["consumption"] == -500

    def test_reading_zero_consumption(self):
        """Verify zero consumption is allowed."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/meter-readings",
            json={
                "meter_id": str(uuid4()),
                "reading_date": "2025-01-15",
                "previous_reading": 1000,
                "current_reading": 1000,
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code == 201
        assert response.json()["consumption"] == 0

    def test_get_nonexistent_meter(self):
        """Verify getting nonexistent meter returns 404."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.get(f"/api/v1/meters/{uuid4()}", headers=_headers(tenant_id))

        assert response.status_code == 404

    def test_meter_utility_type_enum(self):
        """Verify all utility types work."""
        client = TestClient(app)
        tenant_id = uuid4()

        for utility in ["electricity", "water", "gas", "heat", "other"]:
            response = client.post(
                "/api/v1/meters",
                json={
                    "unit_id": str(uuid4()),
                    "meter_number": f"MTR-{utility}",
                    "utility_type": utility,
                },
                headers=_headers(tenant_id),
            )
            assert response.status_code == 201
            assert response.json()["utility_type"] == utility

    def test_meter_status_enum(self):
        """Verify all meter statuses work (via update)."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        for status in ["active", "inactive"]:
            # Create meter
            create_response = client.post(
                "/api/v1/meters",
                json={
                    "unit_id": str(uuid4()),
                    "meter_number": f"MTR-{status}",
                    "utility_type": "electricity",
                },
                headers=headers,
            )
            assert create_response.status_code == 201

            meter_id = create_response.json()["id"]

            # Update to target status
            update_response = client.patch(
                f"/api/v1/meters/{meter_id}",
                json={"status": status},
                headers=headers,
            )
            assert update_response.status_code == 200
            assert update_response.json()["status"] == status
