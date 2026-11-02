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


def test_resolve_tenant_by_custom_domain_takes_priority_over_subdomain() -> None:
    client = TestClient(app)
    unique = uuid4().hex[:8]
    client.post(
        "/api/v1/tenants",
        json={
            "name": "Acme Portfolio",
            "subdomain": f"notmatching-{unique}",
            "custom_domain": f"portal-{unique}.example.com",
        },
    )

    resolved = client.get("/api/v1/tenants/resolve", params={"host": f"portal-{unique}.example.com:443"})

    assert resolved.status_code == 200
    assert resolved.json()["custom_domain"] == f"portal-{unique}.example.com"


def test_resolve_tenant_by_subdomain_when_no_custom_domain_matches() -> None:
    client = TestClient(app)
    unique = uuid4().hex[:8]
    client.post("/api/v1/tenants", json={"name": "Beacon Group", "subdomain": f"beacon-{unique}"})

    resolved = client.get("/api/v1/tenants/resolve", params={"host": f"beacon-{unique}.crepro.app"})

    assert resolved.status_code == 200
    assert resolved.json()["subdomain"] == f"beacon-{unique}"


def test_resolve_tenant_returns_404_when_host_matches_nothing() -> None:
    client = TestClient(app)

    resolved = client.get("/api/v1/tenants/resolve", params={"host": "no-such-tenant.example.com"})

    assert resolved.status_code == 404
