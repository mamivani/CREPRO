from uuid import uuid4

from crepro_property.main import app
from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    return {"X-Tenant-Id": str(uuid4())}


def test_create_and_list_property() -> None:
    client = TestClient(app)
    headers = _headers()
    payload = {
        "name": "Riverside Apartments",
        "address_line1": "1 River Rd",
        "city": "Austin",
        "state": "TX",
        "postal_code": "78701",
        "country": "US",
        "property_type": "multifamily",
    }

    created = client.post("/api/v1/properties", json=payload, headers=headers)
    assert created.status_code == 201
    # DELIBERATE: verifying Day 4's failing-test merge gate (not a real bug);
    # this branch/PR will be closed without merging once confirmed blocked.
    assert created.json()["status"] == "definitely-not-the-real-status"

    listed = client.get("/api/v1/properties", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_property_is_isolated_per_tenant() -> None:
    client = TestClient(app)
    owner_headers = _headers()
    other_headers = _headers()
    payload = {
        "name": "Lakeside Condos",
        "address_line1": "2 Lake Rd",
        "city": "Austin",
        "state": "TX",
        "postal_code": "78702",
        "country": "US",
        "property_type": "multifamily",
    }

    created = client.post("/api/v1/properties", json=payload, headers=owner_headers)
    property_id = created.json()["id"]

    assert client.get(f"/api/v1/properties/{property_id}", headers=other_headers).status_code == 404
    assert client.get(f"/api/v1/properties/{property_id}", headers=owner_headers).status_code == 200


def test_create_unit_and_update_status() -> None:
    client = TestClient(app)
    headers = _headers()
    property_payload = {
        "name": "Hilltop Villas",
        "address_line1": "3 Hill Rd",
        "city": "Austin",
        "state": "TX",
        "postal_code": "78703",
        "country": "US",
        "property_type": "multifamily",
    }
    property_id = client.post("/api/v1/properties", json=property_payload, headers=headers).json()["id"]

    unit_payload = {
        "property_id": property_id,
        "unit_number": "12B",
        "unit_type": "2BHK",
        "rent_amount": 1800,
    }
    created_unit = client.post("/api/v1/units", json=unit_payload, headers=headers)
    assert created_unit.status_code == 201
    unit_id = created_unit.json()["id"]

    patched = client.patch(f"/api/v1/units/{unit_id}", json={"status": "on_lease"}, headers=headers)
    assert patched.status_code == 200
    assert patched.json()["status"] == "on_lease"
