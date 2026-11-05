"""Comprehensive tests for payment service: payment records and security deposits."""

from uuid import UUID, uuid4

import pytest
from crepro_payment.main import app
from crepro_payment.repository import payments, security_deposits
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_repositories():
    """Reset in-memory repositories before each test."""
    payments._rows.clear()
    security_deposits._rows.clear()
    yield
    payments._rows.clear()
    security_deposits._rows.clear()


def _headers(tenant_id: UUID | None = None) -> dict[str, str]:
    """Generate request headers with tenant context."""
    if tenant_id is None:
        tenant_id = uuid4()
    return {"X-Tenant-Id": str(tenant_id)}


class TestPaymentRecordCRUD:
    """Test PaymentRecord CRUD operations."""

    def test_create_payment_minimal(self):
        """Create a payment with required fields only."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/payments",
            json={
                "lease_id": str(uuid4()),
                "resident_id": str(uuid4()),
                "amount": 5000,
                "method": "ach",
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == 5000
        assert data["method"] == "ach"
        assert data["status"] == "pending"
        assert data["currency"] == "USD"

    def test_create_payment_with_all_fields(self):
        """Create a payment with all optional fields."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/payments",
            json={
                "lease_id": str(uuid4()),
                "resident_id": str(uuid4()),
                "amount": 5000,
                "currency": "USD",
                "method": "card",
                "reference": "REF-12345",
                "received_at": "2025-01-15T10:30:00",
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["reference"] == "REF-12345"
        assert data["status"] == "pending"  # Default status

    def test_get_payment(self):
        """Retrieve a payment."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        create_response = client.post(
            "/api/v1/payments",
            json={
                "lease_id": str(uuid4()),
                "resident_id": str(uuid4()),
                "amount": 5000,
                "method": "ach",
            },
            headers=headers,
        )

        payment_id = create_response.json()["id"]

        get_response = client.get(f"/api/v1/payments/{payment_id}", headers=headers)

        assert get_response.status_code == 200
        assert get_response.json()["id"] == payment_id

    def test_update_payment(self):
        """Update a payment."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        create_response = client.post(
            "/api/v1/payments",
            json={
                "lease_id": str(uuid4()),
                "resident_id": str(uuid4()),
                "amount": 5000,
                "method": "ach",
            },
            headers=headers,
        )

        payment_id = create_response.json()["id"]

        update_response = client.patch(
            f"/api/v1/payments/{payment_id}",
            json={"status": "completed", "posted_to_erp": True},
            headers=headers,
        )

        assert update_response.status_code == 200
        assert update_response.json()["status"] == "completed"
        assert update_response.json()["posted_to_erp"]

    def test_delete_payment(self):
        """Delete a payment."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        create_response = client.post(
            "/api/v1/payments",
            json={
                "lease_id": str(uuid4()),
                "resident_id": str(uuid4()),
                "amount": 5000,
                "method": "ach",
            },
            headers=headers,
        )

        payment_id = create_response.json()["id"]

        delete_response = client.delete(f"/api/v1/payments/{payment_id}", headers=headers)

        assert delete_response.status_code == 204

        get_response = client.get(f"/api/v1/payments/{payment_id}", headers=headers)
        assert get_response.status_code == 404

    def test_list_payments(self):
        """List payments for a tenant."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        for i in range(3):
            client.post(
                "/api/v1/payments",
                json={
                    "lease_id": str(uuid4()),
                    "resident_id": str(uuid4()),
                    "amount": 5000 + i * 1000,
                    "method": "ach",
                },
                headers=headers,
            )

        list_response = client.get("/api/v1/payments", headers=headers)

        assert list_response.status_code == 200
        assert len(list_response.json()) == 3


class TestSecurityDepositCRUD:
    """Test SecurityDeposit CRUD operations."""

    def test_create_deposit_minimal(self):
        """Create a security deposit with required fields."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/security-deposits",
            json={
                "lease_id": str(uuid4()),
                "amount": 5000,
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == 5000
        assert data["currency"] == "USD"
        assert data["status"] == "not_required"

    def test_create_deposit_with_optional(self):
        """Create a deposit with optional fields."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/security-deposits",
            json={
                "lease_id": str(uuid4()),
                "amount": 5000,
                "currency": "USD",
                "status": "invoice_raised",
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "invoice_raised"

    def test_get_deposit(self):
        """Retrieve a security deposit."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        create_response = client.post(
            "/api/v1/security-deposits",
            json={
                "lease_id": str(uuid4()),
                "amount": 5000,
            },
            headers=headers,
        )

        deposit_id = create_response.json()["id"]

        get_response = client.get(f"/api/v1/security-deposits/{deposit_id}", headers=headers)

        assert get_response.status_code == 200
        assert get_response.json()["id"] == deposit_id

    def test_update_deposit(self):
        """Update a security deposit."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        create_response = client.post(
            "/api/v1/security-deposits",
            json={
                "lease_id": str(uuid4()),
                "amount": 5000,
            },
            headers=headers,
        )

        deposit_id = create_response.json()["id"]

        update_response = client.patch(
            f"/api/v1/security-deposits/{deposit_id}",
            json={"status": "received", "returned_payment_id": str(uuid4())},
            headers=headers,
        )

        assert update_response.status_code == 200
        assert update_response.json()["status"] == "received"

    def test_list_deposits(self):
        """List security deposits."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        for i in range(2):
            client.post(
                "/api/v1/security-deposits",
                json={
                    "lease_id": str(uuid4()),
                    "amount": 5000 + i * 1000,
                },
                headers=headers,
            )

        list_response = client.get("/api/v1/security-deposits", headers=headers)

        assert list_response.status_code == 200
        assert len(list_response.json()) == 2


class TestPaymentCrossTenantIsolation:
    """Test tenant isolation for payments."""

    def test_payment_isolation_read(self):
        """Verify Tenant B cannot read Tenant A's payment."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()

        create_response = client.post(
            "/api/v1/payments",
            json={
                "lease_id": str(uuid4()),
                "resident_id": str(uuid4()),
                "amount": 5000,
                "method": "ach",
            },
            headers=_headers(tenant_a),
        )

        payment_id = create_response.json()["id"]

        get_response = client.get(f"/api/v1/payments/{payment_id}", headers=_headers(tenant_b))

        assert get_response.status_code == 404

    def test_payment_isolation_list(self):
        """Verify list returns only tenant's payments."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()

        for _ in range(2):
            client.post(
                "/api/v1/payments",
                json={
                    "lease_id": str(uuid4()),
                    "resident_id": str(uuid4()),
                    "amount": 5000,
                    "method": "ach",
                },
                headers=_headers(tenant_a),
            )

        client.post(
            "/api/v1/payments",
            json={
                "lease_id": str(uuid4()),
                "resident_id": str(uuid4()),
                "amount": 3000,
                "method": "check",
            },
            headers=_headers(tenant_b),
        )

        list_a = client.get("/api/v1/payments", headers=_headers(tenant_a))
        list_b = client.get("/api/v1/payments", headers=_headers(tenant_b))

        assert len(list_a.json()) == 2
        assert len(list_b.json()) == 1

    def test_deposit_isolation_update(self):
        """Verify Tenant B cannot update Tenant A's deposit."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()

        create_response = client.post(
            "/api/v1/security-deposits",
            json={
                "lease_id": str(uuid4()),
                "amount": 5000,
            },
            headers=_headers(tenant_a),
        )

        deposit_id = create_response.json()["id"]

        update_response = client.patch(
            f"/api/v1/security-deposits/{deposit_id}",
            json={"status": "received"},
            headers=_headers(tenant_b),
        )

        assert update_response.status_code == 404

    def test_deposit_isolation_delete(self):
        """Verify Tenant B cannot delete Tenant A's deposit."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()

        create_response = client.post(
            "/api/v1/security-deposits",
            json={
                "lease_id": str(uuid4()),
                "amount": 5000,
            },
            headers=_headers(tenant_a),
        )

        deposit_id = create_response.json()["id"]

        delete_response = client.delete(
            f"/api/v1/security-deposits/{deposit_id}",
            headers=_headers(tenant_b),
        )

        assert delete_response.status_code == 404


class TestPaymentSchema:
    """Test payment schema validation."""

    def test_payment_invalid_method(self):
        """Verify invalid payment method is rejected."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/payments",
            json={
                "lease_id": str(uuid4()),
                "resident_id": str(uuid4()),
                "amount": 5000,
                "method": "invalid_method",
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code >= 400

    def test_payment_invalid_status(self):
        """Verify invalid payment status is rejected on update."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)

        create_response = client.post(
            "/api/v1/payments",
            json={
                "lease_id": str(uuid4()),
                "resident_id": str(uuid4()),
                "amount": 5000,
                "method": "ach",
            },
            headers=headers,
        )

        payment_id = create_response.json()["id"]

        response = client.patch(
            f"/api/v1/payments/{payment_id}",
            json={"status": "invalid_status"},
            headers=headers,
        )

        assert response.status_code >= 400

    def test_deposit_invalid_status(self):
        """Verify invalid deposit status is rejected."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/security-deposits",
            json={
                "lease_id": str(uuid4()),
                "amount": 5000,
                "status": "invalid",
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code >= 400

    def test_payment_missing_required_field(self):
        """Verify missing required field is rejected."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/payments",
            json={
                "lease_id": str(uuid4()),
                "resident_id": str(uuid4()),
                "amount": 5000,
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code >= 400


class TestPaymentEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_payment_zero_amount(self):
        """Verify zero payment amount is allowed."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/payments",
            json={
                "lease_id": str(uuid4()),
                "resident_id": str(uuid4()),
                "amount": 0,
                "method": "ach",
            },
            headers=_headers(tenant_id),
        )

        assert response.status_code == 201

    def test_payment_negative_amount(self):
        """Verify negative payment amount is allowed (system allows refunds)."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/payments",
            json={
                "lease_id": str(uuid4()),
                "resident_id": str(uuid4()),
                "amount": -5000,
                "method": "ach",
            },
            headers=_headers(tenant_id),
        )

        # Allow negative amounts for refunds
        assert response.status_code == 201

    def test_deposit_negative_amount(self):
        """Verify negative deposit amount is allowed."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.post(
            "/api/v1/security-deposits",
            json={
                "lease_id": str(uuid4()),
                "amount": -5000,
            },
            headers=_headers(tenant_id),
        )

        # Allow negative amounts
        assert response.status_code == 201

    def test_get_nonexistent_payment(self):
        """Verify getting nonexistent payment returns 404."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.get(
            f"/api/v1/payments/{uuid4()}",
            headers=_headers(tenant_id),
        )

        assert response.status_code == 404

    def test_update_nonexistent_deposit(self):
        """Verify updating nonexistent deposit returns 404."""
        client = TestClient(app)
        tenant_id = uuid4()

        response = client.patch(
            f"/api/v1/security-deposits/{uuid4()}",
            json={"status": "received"},
            headers=_headers(tenant_id),
        )

        assert response.status_code == 404

    def test_payment_method_enum(self):
        """Verify all payment methods work."""
        client = TestClient(app)
        tenant_id = uuid4()

        for method in ["ach", "card", "check", "cash", "wire"]:
            response = client.post(
                "/api/v1/payments",
                json={
                    "lease_id": str(uuid4()),
                    "resident_id": str(uuid4()),
                    "amount": 5000,
                    "method": method,
                },
                headers=_headers(tenant_id),
            )
            assert response.status_code == 201
            assert response.json()["method"] == method

    def test_deposit_status_enum(self):
        """Verify all deposit statuses work."""
        client = TestClient(app)
        tenant_id = uuid4()

        for status in ["invoice_raised", "received", "returned"]:
            response = client.post(
                "/api/v1/security-deposits",
                json={
                    "lease_id": str(uuid4()),
                    "amount": 5000,
                    "status": status,
                },
                headers=_headers(tenant_id),
            )
            assert response.status_code == 201
            assert response.json()["status"] == status
