"""Comprehensive tests for document service: documents and insurance policies."""

import pytest
from uuid import uuid4, UUID
from datetime import date

from crepro_document.main import app
from crepro_document.models import (
    Document, InsurancePolicy,
    DocumentOwnerType, DocumentCategory
)
from crepro_document.repository import documents, insurance_policies
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_repositories():
    """Reset in-memory repositories before each test."""
    documents._rows.clear()
    insurance_policies._rows.clear()
    yield
    documents._rows.clear()
    insurance_policies._rows.clear()


def _headers(tenant_id: UUID | None = None) -> dict[str, str]:
    """Generate request headers with tenant context."""
    if tenant_id is None:
        tenant_id = uuid4()
    return {"X-Tenant-Id": str(tenant_id)}


class TestDocumentCRUD:
    """Test Document CRUD operations."""

    def test_create_document_minimal(self):
        """Create a document with required fields only."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/documents",
            json={
                "owner_type": "property",
                "owner_id": str(uuid4()),
                "file_name": "deed.pdf",
                "storage_path": "/storage/2025/deed.pdf",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["file_name"] == "deed.pdf"
        assert data["category"] == "other"
        assert data["content_type"] == "application/octet-stream"

    def test_create_document_with_all_fields(self):
        """Create a document with all optional fields."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/documents",
            json={
                "owner_type": "lease",
                "owner_id": str(uuid4()),
                "category": "lease_agreement",
                "file_name": "lease_2025.pdf",
                "content_type": "application/pdf",
                "storage_path": "/storage/leases/lease_2025.pdf",
                "uploaded_by": "admin@example.com",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["category"] == "lease_agreement"
        assert data["uploaded_by"] == "admin@example.com"

    def test_get_document(self):
        """Retrieve a document."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        create_response = client.post(
            "/api/v1/documents",
            json={
                "owner_type": "property",
                "owner_id": str(uuid4()),
                "file_name": "photo.jpg",
                "storage_path": "/storage/photos/photo.jpg",
            },
            headers=headers,
        )
        
        document_id = create_response.json()["id"]
        
        get_response = client.get(f"/api/v1/documents/{document_id}", headers=headers)
        
        assert get_response.status_code == 200
        assert get_response.json()["id"] == document_id

    def test_update_document(self):
        """Update a document."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        create_response = client.post(
            "/api/v1/documents",
            json={
                "owner_type": "property",
                "owner_id": str(uuid4()),
                "file_name": "photo.jpg",
                "storage_path": "/storage/photos/photo.jpg",
            },
            headers=headers,
        )
        
        document_id = create_response.json()["id"]
        
        update_response = client.patch(
            f"/api/v1/documents/{document_id}",
            json={"category": "photo", "uploaded_by": "user@example.com"},
            headers=headers,
        )
        
        assert update_response.status_code == 200
        assert update_response.json()["category"] == "photo"

    def test_list_documents(self):
        """List documents for a tenant."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        for i in range(3):
            client.post(
                "/api/v1/documents",
                json={
                    "owner_type": "property",
                    "owner_id": str(uuid4()),
                    "file_name": f"doc{i}.pdf",
                    "storage_path": f"/storage/doc{i}.pdf",
                },
                headers=headers,
            )
        
        list_response = client.get("/api/v1/documents", headers=headers)
        
        assert list_response.status_code == 200
        assert len(list_response.json()) == 3


class TestInsurancePolicyCRUD:
    """Test InsurancePolicy CRUD operations."""

    def test_create_policy_minimal(self):
        """Create a policy with required fields."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/insurance-policies",
            json={
                "property_id": str(uuid4()),
                "provider_name": "InsureCorp",
                "policy_number": "POL-2025-001",
                "effective_date": "2025-01-01",
                "expiration_date": "2026-01-01",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["provider_name"] == "InsureCorp"
        assert data["policy_number"] == "POL-2025-001"

    def test_create_policy_with_all_fields(self):
        """Create a policy with all optional fields."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/insurance-policies",
            json={
                "property_id": str(uuid4()),
                "provider_name": "AllRisk Insurance",
                "policy_type": "building",
                "policy_number": "POL-2025-002",
                "premium_amount": 15000,
                "currency": "USD",
                "effective_date": "2025-01-01",
                "expiration_date": "2026-01-01",
                "description": "Comprehensive building coverage",
                "document_id": str(uuid4()),
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["policy_type"] == "building"
        assert data["premium_amount"] == 15000
        assert data["description"] == "Comprehensive building coverage"

    def test_get_policy(self):
        """Retrieve a policy."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        create_response = client.post(
            "/api/v1/insurance-policies",
            json={
                "property_id": str(uuid4()),
                "provider_name": "TestInsurance",
                "policy_number": "TEST-001",
                "effective_date": "2025-01-01",
                "expiration_date": "2026-01-01",
            },
            headers=headers,
        )
        
        policy_id = create_response.json()["id"]
        
        get_response = client.get(f"/api/v1/insurance-policies/{policy_id}", headers=headers)
        
        assert get_response.status_code == 200

    def test_update_policy(self):
        """Update a policy."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        create_response = client.post(
            "/api/v1/insurance-policies",
            json={
                "property_id": str(uuid4()),
                "provider_name": "TestInsurance",
                "policy_number": "TEST-001",
                "effective_date": "2025-01-01",
                "expiration_date": "2026-01-01",
            },
            headers=headers,
        )
        
        policy_id = create_response.json()["id"]
        
        update_response = client.patch(
            f"/api/v1/insurance-policies/{policy_id}",
            json={"premium_amount": 20000, "policy_type": "liability"},
            headers=headers,
        )
        
        assert update_response.status_code == 200
        assert update_response.json()["premium_amount"] == 20000

    def test_list_policies(self):
        """List policies for a tenant."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        for i in range(2):
            client.post(
                "/api/v1/insurance-policies",
                json={
                    "property_id": str(uuid4()),
                    "provider_name": f"Provider {i}",
                    "policy_number": f"POL-{i}",
                    "effective_date": "2025-01-01",
                    "expiration_date": "2026-01-01",
                },
                headers=headers,
            )
        
        list_response = client.get("/api/v1/insurance-policies", headers=headers)
        
        assert list_response.status_code == 200
        assert len(list_response.json()) == 2


class TestDocumentCrossTenantIsolation:
    """Test tenant isolation for documents."""

    def test_document_isolation_read(self):
        """Verify Tenant B cannot read Tenant A's document."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        create_response = client.post(
            "/api/v1/documents",
            json={
                "owner_type": "property",
                "owner_id": str(uuid4()),
                "file_name": "secret.pdf",
                "storage_path": "/storage/secret.pdf",
            },
            headers=_headers(tenant_a),
        )
        
        document_id = create_response.json()["id"]
        
        get_response = client.get(
            f"/api/v1/documents/{document_id}",
            headers=_headers(tenant_b),
        )
        
        assert get_response.status_code == 404

    def test_document_isolation_list(self):
        """Verify list returns only tenant's documents."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        for _ in range(2):
            client.post(
                "/api/v1/documents",
                json={
                    "owner_type": "property",
                    "owner_id": str(uuid4()),
                    "file_name": "doc.pdf",
                    "storage_path": "/storage/doc.pdf",
                },
                headers=_headers(tenant_a),
            )
        
        client.post(
            "/api/v1/documents",
            json={
                "owner_type": "property",
                "owner_id": str(uuid4()),
                "file_name": "other.pdf",
                "storage_path": "/storage/other.pdf",
            },
            headers=_headers(tenant_b),
        )
        
        list_a = client.get("/api/v1/documents", headers=_headers(tenant_a))
        list_b = client.get("/api/v1/documents", headers=_headers(tenant_b))
        
        assert len(list_a.json()) == 2
        assert len(list_b.json()) == 1

    def test_policy_isolation_update(self):
        """Verify Tenant B cannot update Tenant A's policy."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        create_response = client.post(
            "/api/v1/insurance-policies",
            json={
                "property_id": str(uuid4()),
                "provider_name": "InsureCorp",
                "policy_number": "POL-001",
                "effective_date": "2025-01-01",
                "expiration_date": "2026-01-01",
            },
            headers=_headers(tenant_a),
        )
        
        policy_id = create_response.json()["id"]
        
        update_response = client.patch(
            f"/api/v1/insurance-policies/{policy_id}",
            json={"premium_amount": 99999},
            headers=_headers(tenant_b),
        )
        
        assert update_response.status_code == 404


class TestDocumentSchema:
    """Test document schema validation."""

    def test_document_invalid_owner_type(self):
        """Verify invalid owner type is rejected."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/documents",
            json={
                "owner_type": "invalid",
                "owner_id": str(uuid4()),
                "file_name": "doc.pdf",
                "storage_path": "/storage/doc.pdf",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code >= 400

    def test_document_invalid_category(self):
        """Verify invalid category is rejected."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/documents",
            json={
                "owner_type": "property",
                "owner_id": str(uuid4()),
                "category": "invalid",
                "file_name": "doc.pdf",
                "storage_path": "/storage/doc.pdf",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code >= 400

    def test_policy_invalid_date_range(self):
        """Verify date ranges are accepted (no validation)."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/insurance-policies",
            json={
                "property_id": str(uuid4()),
                "provider_name": "InsureCorp",
                "policy_number": "POL-001",
                "effective_date": "2026-01-01",
                "expiration_date": "2025-01-01",
            },
            headers=_headers(tenant_id),
        )
        
        # No validation - system accepts any date range
        assert response.status_code == 201

    def test_document_missing_required_field(self):
        """Verify missing required field is rejected."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/documents",
            json={
                "owner_type": "property",
                "owner_id": str(uuid4()),
                "file_name": "doc.pdf",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code >= 400


class TestDocumentEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_policy_zero_premium(self):
        """Verify zero premium is allowed."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/insurance-policies",
            json={
                "property_id": str(uuid4()),
                "provider_name": "InsureCorp",
                "policy_number": "POL-001",
                "premium_amount": 0,
                "effective_date": "2025-01-01",
                "expiration_date": "2026-01-01",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201

    def test_policy_negative_premium(self):
        """Verify negative premium is allowed."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/insurance-policies",
            json={
                "property_id": str(uuid4()),
                "provider_name": "InsureCorp",
                "policy_number": "POL-001",
                "premium_amount": -1000,
                "effective_date": "2025-01-01",
                "expiration_date": "2026-01-01",
            },
            headers=_headers(tenant_id),
        )
        
        # Allow negative premiums
        assert response.status_code == 201

    def test_get_nonexistent_document(self):
        """Verify getting nonexistent document returns 404."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.get(
            f"/api/v1/documents/{uuid4()}",
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 404

    def test_document_owner_types_enum(self):
        """Verify all document owner types work."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        for owner_type in ["property", "unit", "lease", "resident"]:
            response = client.post(
                "/api/v1/documents",
                json={
                    "owner_type": owner_type,
                    "owner_id": str(uuid4()),
                    "file_name": "doc.pdf",
                    "storage_path": "/storage/doc.pdf",
                },
                headers=_headers(tenant_id),
            )
            assert response.status_code == 201
            assert response.json()["owner_type"] == owner_type

    def test_document_category_enum(self):
        """Verify all document categories work."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        for category in ["photo", "lease_agreement", "inspection_report"]:
            response = client.post(
                "/api/v1/documents",
                json={
                    "owner_type": "property",
                    "owner_id": str(uuid4()),
                    "category": category,
                    "file_name": "doc.pdf",
                    "storage_path": "/storage/doc.pdf",
                },
                headers=_headers(tenant_id),
            )
            assert response.status_code == 201
            assert response.json()["category"] == category
