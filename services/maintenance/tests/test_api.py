from datetime import date
from uuid import uuid4

from crepro_maintenance.main import app
from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    return {"X-Tenant-Id": str(uuid4())}


def test_create_maintenance_request_defaults() -> None:
    client = TestClient(app)
    headers = _headers()

    created = client.post(
        "/api/v1/maintenance-requests",
        json={"property_id": str(uuid4()), "title": "Leaking faucet"},
        headers=headers,
    )

    assert created.status_code == 201
    assert created.json()["status"] == "open"
    assert created.json()["priority"] == "medium"


def test_assign_and_complete_request() -> None:
    client = TestClient(app)
    headers = _headers()
    request_id = client.post(
        "/api/v1/maintenance-requests",
        json={"property_id": str(uuid4()), "title": "Broken elevator"},
        headers=headers,
    ).json()["id"]

    patched = client.patch(
        f"/api/v1/maintenance-requests/{request_id}",
        json={"status": "completed", "assigned_to": "Vendor Co"},
        headers=headers,
    )

    assert patched.status_code == 200
    assert patched.json()["status"] == "completed"


def test_daily_checklist_round_trip() -> None:
    client = TestClient(app)
    headers = _headers()
    area_id = client.post(
        "/api/v1/checklist-areas",
        json={"name": "Lobby", "tasks": ["Sweep", "Check lights"]},
        headers=headers,
    ).json()["id"]

    checklist = client.post(
        "/api/v1/daily-checklists",
        json={
            "property_id": str(uuid4()),
            "checkup_date": str(date.today()),
            "shift": "day",
            "area_id": area_id,
            "items": [{"task_name": "Sweep", "remarks": "Done"}],
        },
        headers=headers,
    )

    assert checklist.status_code == 201
    assert checklist.json()["items"][0]["task_name"] == "Sweep"


def test_inventory_checkout_isolated_per_tenant() -> None:
    client = TestClient(app)
    owner_headers = _headers()
    other_headers = _headers()
    set_id = client.post(
        "/api/v1/inventory-sets",
        json={"kind": "key", "name": "Unit 4B keys"},
        headers=owner_headers,
    ).json()["id"]

    assert client.get(f"/api/v1/inventory-sets/{set_id}", headers=other_headers).status_code == 404
