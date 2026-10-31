from uuid import uuid4

from crepro_erp_adapter.main import app
from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    return {"X-Tenant-Id": str(uuid4())}


def test_create_ledger_entry_defaults_to_pending() -> None:
    client = TestClient(app)

    created = client.post(
        "/api/v1/ledger-entries",
        json={
            "platform_entity_id": str(uuid4()),
            "event_type": "payment_posted",
            "external_doctype": "Payment Entry",
            "payload_hash": "abc123",
        },
        headers=_headers(),
    )

    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    assert created.json()["attempts"] == 0


def test_mark_ledger_entry_posted() -> None:
    client = TestClient(app)
    headers = _headers()
    entry_id = client.post(
        "/api/v1/ledger-entries",
        json={
            "platform_entity_id": str(uuid4()),
            "event_type": "invoice_generated",
            "external_doctype": "Sales Invoice",
            "payload_hash": "def456",
        },
        headers=headers,
    ).json()["id"]

    patched = client.patch(
        f"/api/v1/ledger-entries/{entry_id}",
        json={"status": "posted", "external_name": "SINV-0001"},
        headers=headers,
    )

    assert patched.json()["status"] == "posted"
    assert patched.json()["external_name"] == "SINV-0001"


def test_tenant_mapping_round_trip() -> None:
    client = TestClient(app)
    headers = _headers()

    created = client.post(
        "/api/v1/tenant-mappings",
        json={"tier": "shared", "external_erp_target": "company-001"},
        headers=headers,
    )

    assert created.status_code == 201
    assert created.json()["tier"] == "shared"


def test_ledger_entry_is_isolated_per_tenant() -> None:
    client = TestClient(app)
    owner_headers = _headers()
    other_headers = _headers()
    entry_id = client.post(
        "/api/v1/ledger-entries",
        json={
            "platform_entity_id": str(uuid4()),
            "event_type": "customer_upserted",
            "external_doctype": "Customer",
            "payload_hash": "ghi789",
        },
        headers=owner_headers,
    ).json()["id"]

    assert client.get(f"/api/v1/ledger-entries/{entry_id}", headers=other_headers).status_code == 404
