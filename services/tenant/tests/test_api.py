from uuid import uuid4

from crepro_tenant.main import app
from fastapi.testclient import TestClient


def test_create_tenant_defaults_to_pending_shared() -> None:
    client = TestClient(app)

    created = client.post(
        "/api/v1/tenants", json={"name": "Riverside Property Group", "subdomain": "riverside"}
    )

    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    assert created.json()["tier"] == "shared"


def test_activate_tenant_and_promote_to_dedicated() -> None:
    client = TestClient(app)
    tenant_id = client.post(
        "/api/v1/tenants", json={"name": "Lakeside Holdings", "subdomain": "lakeside"}
    ).json()["id"]

    patched = client.patch(f"/api/v1/tenants/{tenant_id}", json={"status": "active", "tier": "dedicated"})

    assert patched.status_code == 200
    assert patched.json()["status"] == "active"
    assert patched.json()["tier"] == "dedicated"


def test_list_tenants_includes_created_rows() -> None:
    client = TestClient(app)
    client.post("/api/v1/tenants", json={"name": "Hilltop Communities", "subdomain": "hilltop"})

    listed = client.get("/api/v1/tenants")

    assert listed.status_code == 200
    assert any(row["subdomain"] == "hilltop" for row in listed.json())


def test_get_missing_tenant_returns_404() -> None:
    client = TestClient(app)

    assert client.get(f"/api/v1/tenants/{uuid4()}").status_code == 404
