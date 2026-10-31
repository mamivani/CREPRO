from datetime import date, timedelta
from uuid import uuid4

from crepro_lease.main import app
from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    return {"X-Tenant-Id": str(uuid4())}


def test_create_lease_defaults_to_draft() -> None:
    client = TestClient(app)
    headers = _headers()
    payload = {
        "property_id": str(uuid4()),
        "unit_id": str(uuid4()),
        "resident_id": str(uuid4()),
        "start_date": str(date.today()),
        "end_date": str(date.today() + timedelta(days=365)),
    }

    created = client.post("/api/v1/leases", json=payload, headers=headers)

    assert created.status_code == 201
    assert created.json()["status"] == "draft"
    assert created.json()["frequency"] == "monthly"


def test_activate_lease_and_add_charge() -> None:
    client = TestClient(app)
    headers = _headers()
    lease_payload = {
        "property_id": str(uuid4()),
        "unit_id": str(uuid4()),
        "resident_id": str(uuid4()),
        "start_date": str(date.today()),
        "end_date": str(date.today() + timedelta(days=365)),
    }
    lease_id = client.post("/api/v1/leases", json=lease_payload, headers=headers).json()["id"]

    activated = client.patch(f"/api/v1/leases/{lease_id}", json={"status": "active"}, headers=headers)
    assert activated.json()["status"] == "active"

    charge_payload = {
        "lease_id": lease_id,
        "charge_code": "RENT",
        "amount": 1500,
        "valid_from": str(date.today()),
    }
    charge = client.post("/api/v1/lease-charges", json=charge_payload, headers=headers)
    assert charge.status_code == 201
    assert charge.json()["charge_basis"] == "fixed"


def test_lease_is_isolated_per_tenant() -> None:
    client = TestClient(app)
    owner_headers = _headers()
    other_headers = _headers()
    payload = {
        "property_id": str(uuid4()),
        "unit_id": str(uuid4()),
        "resident_id": str(uuid4()),
        "start_date": str(date.today()),
        "end_date": str(date.today() + timedelta(days=365)),
    }
    lease_id = client.post("/api/v1/leases", json=payload, headers=owner_headers).json()["id"]

    assert client.get(f"/api/v1/leases/{lease_id}", headers=other_headers).status_code == 404


def test_create_resident_defaults_to_prospect() -> None:
    client = TestClient(app)

    created = client.post("/api/v1/residents", json={"full_name": "Jamie Rivera"}, headers=_headers())

    assert created.status_code == 201
    assert created.json()["status"] == "prospect"
    assert created.json()["resident_type"] == "primary"


def test_move_in_resident() -> None:
    client = TestClient(app)
    headers = _headers()
    resident_id = client.post("/api/v1/residents", json={"full_name": "Morgan Lee"}, headers=headers).json()[
        "id"
    ]

    patched = client.patch(
        f"/api/v1/residents/{resident_id}",
        json={"status": "active", "unit_id": str(uuid4())},
        headers=headers,
    )

    assert patched.status_code == 200
    assert patched.json()["status"] == "active"


def test_resident_is_isolated_per_tenant() -> None:
    client = TestClient(app)
    owner_headers = _headers()
    other_headers = _headers()
    resident_id = client.post(
        "/api/v1/residents", json={"full_name": "Casey Nguyen"}, headers=owner_headers
    ).json()["id"]

    assert client.get(f"/api/v1/residents/{resident_id}", headers=other_headers).status_code == 404
