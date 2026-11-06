from crepro_erp_stub.main import app
from fastapi.testclient import TestClient


def _client() -> TestClient:
    client = TestClient(app)
    client.post("/api/test/reset")
    return client


def test_health() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_assigns_auto_numbered_name() -> None:
    client = _client()

    created = client.post("/api/resource/Customer", json={"customer_name": "Acme"})

    assert created.status_code == 200
    data = created.json()["data"]
    assert data["name"] == "CUST-0001"
    assert data["customer_name"] == "Acme"
    assert "modified" in data


def test_create_increments_name_per_doctype() -> None:
    client = _client()

    first = client.post("/api/resource/Customer", json={"customer_name": "A"}).json()["data"]
    second = client.post("/api/resource/Customer", json={"customer_name": "B"}).json()["data"]
    other_doctype = client.post("/api/resource/Property", json={"name": "Bldg"}).json()["data"]

    assert first["name"] == "CUST-0001"
    assert second["name"] == "CUST-0002"
    assert other_doctype["name"] == "PROP-0001"


def test_create_assigns_generic_prefix_for_unmapped_doctype() -> None:
    client = _client()

    created = client.post("/api/resource/Widget", json={}).json()["data"]

    assert created["name"] == "WIDG-0001"


def test_get_by_name() -> None:
    client = _client()
    created = client.post("/api/resource/Customer", json={"customer_name": "Acme"}).json()["data"]

    fetched = client.get(f"/api/resource/Customer/{created['name']}")

    assert fetched.status_code == 200
    assert fetched.json()["data"]["customer_name"] == "Acme"


def test_get_by_name_404_when_missing() -> None:
    client = _client()

    response = client.get("/api/resource/Customer/CUST-9999")

    assert response.status_code == 404


def test_list_returns_all_records() -> None:
    client = _client()
    client.post("/api/resource/Customer", json={"customer_name": "A"})
    client.post("/api/resource/Customer", json={"customer_name": "B"})

    response = client.get("/api/resource/Customer")

    assert response.status_code == 200
    assert len(response.json()["data"]) == 2


def test_list_respects_limit_page_length() -> None:
    client = _client()
    for i in range(5):
        client.post("/api/resource/Customer", json={"customer_name": f"C{i}"})

    response = client.get("/api/resource/Customer", params={"limit_page_length": 2})

    assert len(response.json()["data"]) == 2


def test_list_filters_by_equality() -> None:
    client = _client()
    created = client.post(
        "/api/resource/Customer", json={"customer_name": "Acme", "custom_platform_id": "abc-123"}
    ).json()["data"]
    client.post("/api/resource/Customer", json={"customer_name": "Other", "custom_platform_id": "xyz"})

    response = client.get(
        "/api/resource/Customer",
        params={"filters": '[["custom_platform_id","=","abc-123"]]'},
    )

    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["name"] == created["name"]


def test_list_filters_by_modified_since_and_orders_ascending() -> None:
    client = _client()
    client.post("/api/resource/Customer", json={"customer_name": "A"})
    second = client.post("/api/resource/Customer", json={"customer_name": "B"}).json()["data"]

    response = client.get(
        "/api/resource/Customer",
        params={
            "filters": f'[["modified",">=","{second["modified"]}"]]',
            "order_by": "modified asc",
        },
    )

    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["name"] == second["name"]


def test_list_ignores_malformed_filters() -> None:
    client = _client()
    client.post("/api/resource/Customer", json={"customer_name": "A"})

    response = client.get("/api/resource/Customer", params={"filters": "not-json"})

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


def test_list_ignores_unsupported_operator() -> None:
    client = _client()
    client.post("/api/resource/Customer", json={"customer_name": "A", "amount": 10})

    response = client.get(
        "/api/resource/Customer",
        params={"filters": '[["amount","!=","5"]]'},
    )

    assert len(response.json()["data"]) == 1


def test_update_patches_fields() -> None:
    client = _client()
    created = client.post("/api/resource/Customer", json={"customer_name": "Acme"}).json()["data"]

    updated = client.patch(f"/api/resource/Customer/{created['name']}", json={"email_id": "a@b.com"})

    assert updated.status_code == 200
    assert updated.json()["data"]["email_id"] == "a@b.com"
    assert updated.json()["data"]["customer_name"] == "Acme"


def test_update_404_when_missing() -> None:
    client = _client()

    response = client.patch("/api/resource/Customer/CUST-9999", json={})

    assert response.status_code == 404


def test_delete_removes_record() -> None:
    client = _client()
    created = client.post("/api/resource/Customer", json={"customer_name": "Acme"}).json()["data"]

    deleted = client.delete(f"/api/resource/Customer/{created['name']}")
    assert deleted.status_code == 202

    assert client.get(f"/api/resource/Customer/{created['name']}").status_code == 404


def test_delete_404_when_missing() -> None:
    client = _client()

    response = client.delete("/api/resource/Customer/CUST-9999")

    assert response.status_code == 404


def test_reset_clears_all_doctypes() -> None:
    client = _client()
    client.post("/api/resource/Customer", json={"customer_name": "Acme"})

    client.post("/api/test/reset")

    assert client.get("/api/resource/Customer").json()["data"] == []
