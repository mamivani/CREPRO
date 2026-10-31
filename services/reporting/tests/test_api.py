from uuid import uuid4

from crepro_reporting.main import app
from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    return {"X-Tenant-Id": str(uuid4())}


def test_create_report_definition() -> None:
    client = TestClient(app)

    created = client.post(
        "/api/v1/report-definitions",
        json={"name": "Occupancy by property", "category": "occupancy"},
        headers=_headers(),
    )

    assert created.status_code == 201
    assert created.json()["category"] == "occupancy"


def test_report_definition_is_isolated_per_tenant() -> None:
    client = TestClient(app)
    owner_headers = _headers()
    other_headers = _headers()
    report_id = client.post(
        "/api/v1/report-definitions",
        json={"name": "Maintenance backlog", "category": "maintenance"},
        headers=owner_headers,
    ).json()["id"]

    assert client.get(f"/api/v1/report-definitions/{report_id}", headers=other_headers).status_code == 404
