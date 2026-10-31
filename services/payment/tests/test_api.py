from uuid import uuid4

from crepro_payment.main import app
from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    return {"X-Tenant-Id": str(uuid4())}


def test_create_payment_defaults_to_pending() -> None:
    client = TestClient(app)

    created = client.post(
        "/api/v1/payments",
        json={
            "lease_id": str(uuid4()),
            "resident_id": str(uuid4()),
            "amount": 1500,
            "method": "ach",
        },
        headers=_headers(),
    )

    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    assert created.json()["posted_to_erp"] is False


def test_mark_payment_posted_to_erp() -> None:
    client = TestClient(app)
    headers = _headers()
    payment_id = client.post(
        "/api/v1/payments",
        json={
            "lease_id": str(uuid4()),
            "resident_id": str(uuid4()),
            "amount": 1500,
            "method": "card",
        },
        headers=headers,
    ).json()["id"]

    patched = client.patch(
        f"/api/v1/payments/{payment_id}",
        json={"status": "completed", "posted_to_erp": True, "erp_reference": "PE-0001"},
        headers=headers,
    )

    assert patched.json()["status"] == "completed"
    assert patched.json()["erp_reference"] == "PE-0001"


def test_security_deposit_lifecycle() -> None:
    client = TestClient(app)
    headers = _headers()
    deposit = client.post(
        "/api/v1/security-deposits",
        json={"lease_id": str(uuid4()), "amount": 1500, "status": "invoice_raised"},
        headers=headers,
    )
    assert deposit.status_code == 201
    deposit_id = deposit.json()["id"]

    patched = client.patch(
        f"/api/v1/security-deposits/{deposit_id}", json={"status": "received"}, headers=headers
    )
    assert patched.json()["status"] == "received"


def test_payment_is_isolated_per_tenant() -> None:
    client = TestClient(app)
    owner_headers = _headers()
    other_headers = _headers()
    payment_id = client.post(
        "/api/v1/payments",
        json={"lease_id": str(uuid4()), "resident_id": str(uuid4()), "amount": 500, "method": "cash"},
        headers=owner_headers,
    ).json()["id"]

    assert client.get(f"/api/v1/payments/{payment_id}", headers=other_headers).status_code == 404
