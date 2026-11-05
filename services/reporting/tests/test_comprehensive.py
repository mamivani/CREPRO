"""Comprehensive tests for reporting service: report definitions."""

from uuid import UUID, uuid4

import pytest
from crepro_reporting.main import app
from crepro_reporting.repository import report_definitions
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_repositories():
    """Reset in-memory repositories before each test."""
    report_definitions._rows.clear()
    yield
    report_definitions._rows.clear()


def _headers(tenant_id: UUID | None = None) -> dict[str, str]:
    """Generate request headers with tenant context."""
    if tenant_id is None:
        tenant_id = uuid4()
    return {"X-Tenant-Id": str(tenant_id)}


class TestReportDefinitionCRUD:
    """Test ReportDefinition CRUD operations."""

    def test_create_report_minimal(self):
        """Create a report with required fields only."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/report-definitions",
            json={
                "name": "Occupancy Report",
                "category": "occupancy",
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Occupancy Report"
        assert data["category"] == "occupancy"

    def test_create_report_with_all_fields(self):
        """Create a report with all optional fields."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/report-definitions",
            json={
                "name": "Monthly Financial",
                "category": "financial",
                "description": "Monthly revenue and expenses",
                "query_reference": "QRY-FINANCIAL-001",
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Monthly Financial"
        assert data["description"] == "Monthly revenue and expenses"
        assert data["query_reference"] == "QRY-FINANCIAL-001"

    def test_get_report(self):
        """Retrieve a report."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        create_response = client.post(
            "/api/v1/report-definitions",
            json={
                "name": "Test Report",
                "category": "occupancy",
            },
            headers=headers,
        )

        report_id = create_response.json()["id"]

        get_response = client.get(f"/api/v1/report-definitions/{report_id}", headers=headers)

        assert get_response.status_code == 200
        assert get_response.json()["id"] == report_id

    def test_update_report(self):
        """Update a report."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        create_response = client.post(
            "/api/v1/report-definitions",
            json={
                "name": "Original Report",
                "category": "occupancy",
            },
            headers=headers,
        )

        report_id = create_response.json()["id"]

        update_response = client.patch(
            f"/api/v1/report-definitions/{report_id}",
            json={"description": "New description", "query_reference": "SELECT * FROM tenants"},
            headers=headers,
        )

        assert update_response.status_code == 200
        assert update_response.json()["description"] == "New description"
        assert update_response.json()["query_reference"] == "SELECT * FROM tenants"

    def test_delete_report(self):
        """Delete a report."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        create_response = client.post(
            "/api/v1/report-definitions",
            json={
                "name": "Temp Report",
                "category": "occupancy",
            },
            headers=headers,
        )

        report_id = create_response.json()["id"]

        delete_response = client.delete(
            f"/api/v1/report-definitions/{report_id}",
            headers=headers,
        )

        assert delete_response.status_code == 204

        get_response = client.get(f"/api/v1/report-definitions/{report_id}", headers=headers)
        assert get_response.status_code == 404

    def test_list_reports(self):
        """List reports for a tenant."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        for i in range(3):
            client.post(
                "/api/v1/report-definitions",
                json={
                    "name": f"Report {i}",
                    "category": "occupancy",
                },
                headers=headers,
            )

        list_response = client.get("/api/v1/report-definitions", headers=headers)

        assert list_response.status_code == 200
        assert len(list_response.json()) == 3


class TestReportCrossTenantIsolation:
    """Test tenant isolation for reports."""

    def test_report_isolation_read(self):
        """Verify Tenant B cannot read Tenant A's report."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()

        create_response = client.post(
            "/api/v1/report-definitions",
            json={
                "name": "Secret Report",
                "category": "financial",
            },
            headers=_headers(tenant_a),
        )

        report_id = create_response.json()["id"]

        get_response = client.get(
            f"/api/v1/report-definitions/{report_id}",
            headers=_headers(tenant_b),
        )

        assert get_response.status_code == 404

    def test_report_isolation_list(self):
        """Verify list returns only tenant's reports."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()

        for _ in range(2):
            client.post(
                "/api/v1/report-definitions",
                json={
                    "name": "Report A",
                    "category": "occupancy",
                },
                headers=_headers(tenant_a),
            )

        client.post(
            "/api/v1/report-definitions",
            json={
                "name": "Report B",
                "category": "financial",
            },
            headers=_headers(tenant_b),
        )

        list_a = client.get("/api/v1/report-definitions", headers=_headers(tenant_a))
        list_b = client.get("/api/v1/report-definitions", headers=_headers(tenant_b))

        assert len(list_a.json()) == 2
        assert len(list_b.json()) == 1

    def test_report_isolation_update(self):
        """Verify Tenant B cannot update Tenant A's report."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()

        create_response = client.post(
            "/api/v1/report-definitions",
            json={
                "name": "Report A",
                "category": "occupancy",
            },
            headers=_headers(tenant_a),
        )

        report_id = create_response.json()["id"]

        update_response = client.patch(
            f"/api/v1/report-definitions/{report_id}",
            json={"name": "Modified by B"},
            headers=_headers(tenant_b),
        )

        assert update_response.status_code == 404

    def test_report_isolation_delete(self):
        """Verify Tenant B cannot delete Tenant A's report."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()

        create_response = client.post(
            "/api/v1/report-definitions",
            json={
                "name": "Report A",
                "category": "occupancy",
            },
            headers=_headers(tenant_a),
        )

        report_id = create_response.json()["id"]

        delete_response = client.delete(
            f"/api/v1/report-definitions/{report_id}",
            headers=_headers(tenant_b),
        )

        assert delete_response.status_code == 404


class TestReportSchema:
    """Test report schema validation."""

    def test_report_invalid_category(self):
        """Verify invalid category is rejected."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/report-definitions",
            json={
                "name": "Test",
                "category": "invalid",
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code >= 400

    def test_report_missing_required_field(self):
        """Verify missing required field is rejected."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/report-definitions",
            json={
                "name": "Test Report",
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code >= 400

    def test_report_empty_name(self):
        """Verify empty name is allowed."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/report-definitions",
            json={
                "name": "",
                "category": "occupancy",
            },
            headers=_headers(tenant_id),
        )

        # Allow empty names
        assert response.status_code == 201


class TestReportEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_get_nonexistent_report(self):
        """Verify getting nonexistent report returns 404."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.get(
            f"/api/v1/report-definitions/{uuid4()}",
            headers=_headers(tenant_id),
        )

        assert response.status_code == 404

    def test_update_nonexistent_report(self):
        """Verify updating nonexistent report returns 404."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.patch(
            f"/api/v1/report-definitions/{uuid4()}",
            json={"name": "Updated"},
            headers=_headers(tenant_id),
        )

        assert response.status_code == 404

    def test_delete_nonexistent_report(self):
        """Verify deleting nonexistent report returns 404."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.delete(
            f"/api/v1/report-definitions/{uuid4()}",
            headers=_headers(tenant_id),
        )

        assert response.status_code == 404

    def test_report_category_enum(self):
        """Verify all report categories work."""
        client = TestClient(app)
        tenant_id = uuid4()

        for category in ["occupancy", "financial", "maintenance", "operations"]:
            response = client.post(
                "/api/v1/report-definitions",
                json={
                    "name": f"Report {category}",
                    "category": category,
                },
                headers=_headers(tenant_id),
            )
            assert response.status_code == 201
            assert response.json()["category"] == category

    def test_report_list_empty(self):
        """Verify listing empty reports returns empty list."""
        client = TestClient(app)
        tenant_id = uuid4()

        list_response = client.get(
            "/api/v1/report-definitions",
            headers=_headers(tenant_id),
        )

        assert list_response.status_code == 200
        assert list_response.json() == []

    def test_report_long_description(self):
        """Verify long description is accepted."""
        client = TestClient(app)
        tenant_id = uuid4()

        long_desc = "A" * 1000

        response = client.post(
            "/api/v1/report-definitions",
            json={
                "name": "Test Report",
                "category": "occupancy",
                "description": long_desc,
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code == 201
        assert response.json()["description"] == long_desc

    def test_report_special_characters(self):
        """Verify special characters in name are accepted."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/report-definitions",
            json={
                "name": "Q1 2025 Financial & Occupancy Report (Primary)",
                "category": "financial",
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code == 201
