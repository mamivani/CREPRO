from datetime import date, timedelta
from uuid import uuid4

from crepro_utility.main import app
from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    return {"X-Tenant-Id": str(uuid4())}


def test_create_meter_defaults_to_active() -> None:
    client = TestClient(app)

    created = client.post(
        "/api/v1/meters",
        json={"unit_id": str(uuid4()), "meter_number": "E-1001", "utility_type": "electricity"},
        headers=_headers(),
    )

    assert created.status_code == 201
    assert created.json()["status"] == "active"


def test_meter_reading_computes_consumption() -> None:
    client = TestClient(app)
    headers = _headers()
    meter_id = client.post(
        "/api/v1/meters",
        json={"unit_id": str(uuid4()), "meter_number": "W-2002", "utility_type": "water"},
        headers=headers,
    ).json()["id"]

    reading = client.post(
        "/api/v1/meter-readings",
        json={
            "meter_id": meter_id,
            "reading_date": str(date.today()),
            "previous_reading": 100,
            "current_reading": 150,
        },
        headers=headers,
    )

    assert reading.status_code == 201
    assert reading.json()["consumption"] == 50


def test_meter_is_isolated_per_tenant() -> None:
    client = TestClient(app)
    owner_headers = _headers()
    other_headers = _headers()
    meter_id = client.post(
        "/api/v1/meters",
        json={"unit_id": str(uuid4()), "meter_number": "G-3003", "utility_type": "gas"},
        headers=owner_headers,
    ).json()["id"]

    assert client.get(f"/api/v1/meters/{meter_id}", headers=other_headers).status_code == 404


def test_meter_deactivation() -> None:
    client = TestClient(app)
    headers = _headers()
    meter_id = client.post(
        "/api/v1/meters",
        json={"unit_id": str(uuid4()), "meter_number": "E-4004", "utility_type": "electricity"},
        headers=headers,
    ).json()["id"]

    patched = client.patch(
        f"/api/v1/meters/{meter_id}",
        json={"status": "inactive", "deactivation_date": str(date.today() + timedelta(days=1))},
        headers=headers,
    )

    assert patched.json()["status"] == "inactive"
