from datetime import date, timedelta
from uuid import uuid4

from crepro_reservation.main import app
from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    return {"X-Tenant-Id": str(uuid4())}


def test_create_reservation_defaults_to_pending() -> None:
    client = TestClient(app)

    created = client.post(
        "/api/v1/reservations",
        json={
            "unit_id": str(uuid4()),
            "guest_name": "Taylor Smith",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=3)),
            "nightly_rate": 120,
        },
        headers=_headers(),
    )

    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    assert created.json()["channel"] == "direct"


def test_confirm_reservation() -> None:
    client = TestClient(app)
    headers = _headers()
    reservation_id = client.post(
        "/api/v1/reservations",
        json={
            "unit_id": str(uuid4()),
            "guest_name": "Jordan Blake",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=2)),
            "nightly_rate": 99,
        },
        headers=headers,
    ).json()["id"]

    patched = client.patch(
        f"/api/v1/reservations/{reservation_id}", json={"status": "confirmed"}, headers=headers
    )

    assert patched.json()["status"] == "confirmed"


def test_reservation_is_isolated_per_tenant() -> None:
    client = TestClient(app)
    owner_headers = _headers()
    other_headers = _headers()
    reservation_id = client.post(
        "/api/v1/reservations",
        json={
            "unit_id": str(uuid4()),
            "guest_name": "Sam Rae",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=1)),
            "nightly_rate": 80,
        },
        headers=owner_headers,
    ).json()["id"]

    assert client.get(f"/api/v1/reservations/{reservation_id}", headers=other_headers).status_code == 404
