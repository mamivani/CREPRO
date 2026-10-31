from datetime import date, timedelta
from uuid import uuid4

from crepro_document.main import app
from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    return {"X-Tenant-Id": str(uuid4())}


def test_create_document() -> None:
    client = TestClient(app)

    created = client.post(
        "/api/v1/documents",
        json={
            "owner_type": "lease",
            "owner_id": str(uuid4()),
            "category": "lease_agreement",
            "file_name": "lease.pdf",
            "storage_path": "tenants/abc/lease.pdf",
        },
        headers=_headers(),
    )

    assert created.status_code == 201
    assert created.json()["category"] == "lease_agreement"


def test_insurance_policy_links_to_document() -> None:
    client = TestClient(app)
    headers = _headers()
    document_id = client.post(
        "/api/v1/documents",
        json={
            "owner_type": "insurance_policy",
            "owner_id": str(uuid4()),
            "category": "insurance_certificate",
            "file_name": "policy.pdf",
            "storage_path": "tenants/abc/policy.pdf",
        },
        headers=headers,
    ).json()["id"]

    policy = client.post(
        "/api/v1/insurance-policies",
        json={
            "property_id": str(uuid4()),
            "provider_name": "Acme Insurance",
            "policy_number": "POL-1",
            "effective_date": str(date.today()),
            "expiration_date": str(date.today() + timedelta(days=365)),
            "document_id": document_id,
        },
        headers=headers,
    )

    assert policy.status_code == 201
    assert policy.json()["document_id"] == document_id


def test_document_is_isolated_per_tenant() -> None:
    client = TestClient(app)
    owner_headers = _headers()
    other_headers = _headers()
    document_id = client.post(
        "/api/v1/documents",
        json={
            "owner_type": "property",
            "owner_id": str(uuid4()),
            "file_name": "photo.jpg",
            "storage_path": "tenants/abc/photo.jpg",
        },
        headers=owner_headers,
    ).json()["id"]

    assert client.get(f"/api/v1/documents/{document_id}", headers=other_headers).status_code == 404
