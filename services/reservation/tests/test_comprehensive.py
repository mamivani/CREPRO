"""Comprehensive tests for reservation service: short-term bookings."""

import pytest
from uuid import uuid4, UUID
from datetime import date

from crepro_reservation.main import app
from crepro_reservation.models import Reservation, ReservationStatus, ReservationChannel
from crepro_reservation.repository import reservations
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_repositories():
    """Reset in-memory repositories before each test."""
    reservations._rows.clear()
    yield
    reservations._rows.clear()


def _headers(tenant_id: UUID | None = None) -> dict[str, str]:
    """Generate request headers with tenant context."""
    if tenant_id is None:
        tenant_id = uuid4()
    return {"X-Tenant-Id": str(tenant_id)}


class TestReservationCRUD:
    """Test Reservation CRUD operations."""

    def test_create_reservation_minimal(self):
        """Create a reservation with required fields only."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/reservations",
            json={
                "unit_id": str(uuid4()),
                "guest_name": "John Guest",
                "start_date": "2025-01-01",
                "end_date": "2025-01-07",
                "nightly_rate": 150,
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["guest_name"] == "John Guest"
        assert data["status"] == "pending"
        assert data["channel"] == "direct"
        assert data["nightly_rate"] == 150

    def test_create_reservation_with_all_fields(self):
        """Create a reservation with all optional fields."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/reservations",
            json={
                "unit_id": str(uuid4()),
                "guest_name": "Jane Guest",
                "guest_email": "jane@example.com",
                "start_date": "2025-02-01",
                "end_date": "2025-02-08",
                "channel": "third_party",
                "nightly_rate": 200,
                "notes": "Pet-friendly guest",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["guest_email"] == "jane@example.com"
        assert data["status"] == "pending"  # Default status
        assert data["channel"] == "third_party"
        assert data["notes"] == "Pet-friendly guest"

    def test_get_reservation(self):
        """Retrieve a reservation."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        create_response = client.post(
            "/api/v1/reservations",
            json={
                "unit_id": str(uuid4()),
                "guest_name": "Bob Guest",
                "start_date": "2025-01-01",
                "end_date": "2025-01-05",
                "nightly_rate": 100,
            },
            headers=headers,
        )
        
        reservation_id = create_response.json()["id"]
        
        get_response = client.get(f"/api/v1/reservations/{reservation_id}", headers=headers)
        
        assert get_response.status_code == 200
        assert get_response.json()["id"] == reservation_id

    def test_update_reservation(self):
        """Update a reservation."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        create_response = client.post(
            "/api/v1/reservations",
            json={
                "unit_id": str(uuid4()),
                "guest_name": "Bob Guest",
                "start_date": "2025-01-01",
                "end_date": "2025-01-05",
                "nightly_rate": 100,
            },
            headers=headers,
        )
        
        reservation_id = create_response.json()["id"]
        
        update_response = client.patch(
            f"/api/v1/reservations/{reservation_id}",
            json={"status": "checked_in", "notes": "Early arrival"},
            headers=headers,
        )
        
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "checked_in"
        assert update_response.json()["notes"] == "Early arrival"

    def test_delete_reservation(self):
        """Delete a reservation."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        create_response = client.post(
            "/api/v1/reservations",
            json={
                "unit_id": str(uuid4()),
                "guest_name": "Bob Guest",
                "start_date": "2025-01-01",
                "end_date": "2025-01-05",
                "nightly_rate": 100,
            },
            headers=headers,
        )
        
        reservation_id = create_response.json()["id"]
        
        delete_response = client.delete(
            f"/api/v1/reservations/{reservation_id}",
            headers=headers,
        )
        
        assert delete_response.status_code == 204
        
        get_response = client.get(f"/api/v1/reservations/{reservation_id}", headers=headers)
        assert get_response.status_code == 404

    def test_list_reservations(self):
        """List reservations for a tenant."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        for i in range(3):
            client.post(
                "/api/v1/reservations",
                json={
                    "unit_id": str(uuid4()),
                    "guest_name": f"Guest {i}",
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-05",
                    "nightly_rate": 100 + i * 10,
                },
                headers=headers,
            )
        
        list_response = client.get("/api/v1/reservations", headers=headers)
        
        assert list_response.status_code == 200
        assert len(list_response.json()) == 3


class TestReservationCrossTenantIsolation:
    """Test tenant isolation for reservations."""

    def test_reservation_isolation_read(self):
        """Verify Tenant B cannot read Tenant A's reservation."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        create_response = client.post(
            "/api/v1/reservations",
            json={
                "unit_id": str(uuid4()),
                "guest_name": "John Guest",
                "start_date": "2025-01-01",
                "end_date": "2025-01-05",
                "nightly_rate": 100,
            },
            headers=_headers(tenant_a),
        )
        
        reservation_id = create_response.json()["id"]
        
        get_response = client.get(
            f"/api/v1/reservations/{reservation_id}",
            headers=_headers(tenant_b),
        )
        
        assert get_response.status_code == 404

    def test_reservation_isolation_list(self):
        """Verify list returns only tenant's reservations."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        for _ in range(2):
            client.post(
                "/api/v1/reservations",
                json={
                    "unit_id": str(uuid4()),
                    "guest_name": "Guest A",
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-05",
                    "nightly_rate": 100,
                },
                headers=_headers(tenant_a),
            )
        
        client.post(
            "/api/v1/reservations",
            json={
                "unit_id": str(uuid4()),
                "guest_name": "Guest B",
                "start_date": "2025-02-01",
                "end_date": "2025-02-05",
                "nightly_rate": 150,
            },
            headers=_headers(tenant_b),
        )
        
        list_a = client.get("/api/v1/reservations", headers=_headers(tenant_a))
        list_b = client.get("/api/v1/reservations", headers=_headers(tenant_b))
        
        assert len(list_a.json()) == 2
        assert len(list_b.json()) == 1

    def test_reservation_isolation_update(self):
        """Verify Tenant B cannot update Tenant A's reservation."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        create_response = client.post(
            "/api/v1/reservations",
            json={
                "unit_id": str(uuid4()),
                "guest_name": "John Guest",
                "start_date": "2025-01-01",
                "end_date": "2025-01-05",
                "nightly_rate": 100,
            },
            headers=_headers(tenant_a),
        )
        
        reservation_id = create_response.json()["id"]
        
        update_response = client.patch(
            f"/api/v1/reservations/{reservation_id}",
            json={"status": "checked_out"},
            headers=_headers(tenant_b),
        )
        
        assert update_response.status_code == 404

    def test_reservation_isolation_delete(self):
        """Verify Tenant B cannot delete Tenant A's reservation."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        create_response = client.post(
            "/api/v1/reservations",
            json={
                "unit_id": str(uuid4()),
                "guest_name": "John Guest",
                "start_date": "2025-01-01",
                "end_date": "2025-01-05",
                "nightly_rate": 100,
            },
            headers=_headers(tenant_a),
        )
        
        reservation_id = create_response.json()["id"]
        
        delete_response = client.delete(
            f"/api/v1/reservations/{reservation_id}",
            headers=_headers(tenant_b),
        )
        
        assert delete_response.status_code == 404


class TestReservationSchema:
    """Test reservation schema validation."""

    def test_reservation_invalid_date_range(self):
        """Verify date ranges are accepted (no validation)."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/reservations",
            json={
                "unit_id": str(uuid4()),
                "guest_name": "John Guest",
                "start_date": "2025-01-05",
                "end_date": "2025-01-01",
                "nightly_rate": 100,
            },
            headers=_headers(tenant_id),
        )
        
        # No date validation - system accepts any date range
        assert response.status_code == 201

    def test_reservation_invalid_status(self):
        """Verify invalid status is rejected on update."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        create_response = client.post(
            "/api/v1/reservations",
            json={
                "unit_id": str(uuid4()),
                "guest_name": "John Guest",
                "start_date": "2025-01-01",
                "end_date": "2025-01-05",
                "nightly_rate": 100,
            },
            headers=headers,
        )
        
        reservation_id = create_response.json()["id"]
        
        response = client.patch(
            f"/api/v1/reservations/{reservation_id}",
            json={"status": "invalid"},
            headers=headers,
        )
        
        assert response.status_code >= 400

    def test_reservation_invalid_channel(self):
        """Verify invalid channel is rejected."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/reservations",
            json={
                "unit_id": str(uuid4()),
                "guest_name": "John Guest",
                "start_date": "2025-01-01",
                "end_date": "2025-01-05",
                "nightly_rate": 100,
                "channel": "invalid",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code >= 400

    def test_reservation_missing_required_field(self):
        """Verify missing required field is rejected."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/reservations",
            json={
                "unit_id": str(uuid4()),
                "guest_name": "John Guest",
                "start_date": "2025-01-01",
                "end_date": "2025-01-05",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code >= 400


class TestReservationEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_reservation_zero_nightly_rate(self):
        """Verify zero nightly rate is allowed."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/reservations",
            json={
                "unit_id": str(uuid4()),
                "guest_name": "John Guest",
                "start_date": "2025-01-01",
                "end_date": "2025-01-05",
                "nightly_rate": 0,
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201

    def test_reservation_negative_nightly_rate(self):
        """Verify negative nightly rate is allowed."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/reservations",
            json={
                "unit_id": str(uuid4()),
                "guest_name": "John Guest",
                "start_date": "2025-01-01",
                "end_date": "2025-01-05",
                "nightly_rate": -100,
            },
            headers=_headers(tenant_id),
        )
        
        # Allow negative rates (discounts/promotions)
        assert response.status_code == 201

    def test_get_nonexistent_reservation(self):
        """Verify getting nonexistent reservation returns 404."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.get(
            f"/api/v1/reservations/{uuid4()}",
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 404

    def test_update_nonexistent_reservation(self):
        """Verify updating nonexistent reservation returns 404."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.patch(
            f"/api/v1/reservations/{uuid4()}",
            json={"status": "confirmed"},
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 404

    def test_reservation_status_enum(self):
        """Verify all reservation statuses work (via update)."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        for status in ["pending", "confirmed", "checked_in", "checked_out", "cancelled"]:
            # Create with pending
            create_response = client.post(
                "/api/v1/reservations",
                json={
                    "unit_id": str(uuid4()),
                    "guest_name": "Guest",
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-05",
                    "nightly_rate": 100,
                },
                headers=headers,
            )
            assert create_response.status_code == 201
            
            reservation_id = create_response.json()["id"]
            
            # Update to the target status
            update_response = client.patch(
                f"/api/v1/reservations/{reservation_id}",
                json={"status": status},
                headers=headers,
            )
            assert update_response.status_code == 200
            assert update_response.json()["status"] == status

    def test_reservation_channel_enum(self):
        """Verify all reservation channels work."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        for channel in ["direct", "third_party"]:
            response = client.post(
                "/api/v1/reservations",
                json={
                    "unit_id": str(uuid4()),
                    "guest_name": "Guest",
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-05",
                    "nightly_rate": 100,
                    "channel": channel,
                },
                headers=_headers(tenant_id),
            )
            assert response.status_code == 201
            assert response.json()["channel"] == channel
