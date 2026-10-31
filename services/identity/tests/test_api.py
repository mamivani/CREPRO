from uuid import uuid4

from crepro_identity.main import app
from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    return {"X-Tenant-Id": str(uuid4())}


def test_create_user_defaults_to_invited() -> None:
    client = TestClient(app)

    created = client.post(
        "/api/v1/users",
        json={"email": "pm@example.com", "full_name": "Pat Manager", "role": "property_manager"},
        headers=_headers(),
    )

    assert created.status_code == 201
    assert created.json()["status"] == "invited"


def test_activate_user() -> None:
    client = TestClient(app)
    headers = _headers()
    user_id = client.post(
        "/api/v1/users",
        json={"email": "tech@example.com", "full_name": "Taylor Tech", "role": "maintenance_technician"},
        headers=headers,
    ).json()["id"]

    patched = client.patch(f"/api/v1/users/{user_id}", json={"status": "active"}, headers=headers)

    assert patched.json()["status"] == "active"


def test_user_is_isolated_per_tenant() -> None:
    client = TestClient(app)
    owner_headers = _headers()
    other_headers = _headers()
    user_id = client.post(
        "/api/v1/users",
        json={"email": "admin@example.com", "full_name": "Alex Admin", "role": "system_admin"},
        headers=owner_headers,
    ).json()["id"]

    assert client.get(f"/api/v1/users/{user_id}", headers=other_headers).status_code == 404
