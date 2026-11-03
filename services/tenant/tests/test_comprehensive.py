"""Comprehensive tests for tenant service: tenant directory management."""

import pytest
from uuid import uuid4, UUID

from crepro_tenant.main import app
from crepro_tenant.models import Tenant, TenantTier, TenantOnboardingStatus
from crepro_tenant.repository import tenants
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_repositories():
    """Reset in-memory repositories before each test."""
    tenants._rows.clear()
    yield
    tenants._rows.clear()


class TestTenantCRUD:
    """Test Tenant CRUD operations (no tenant-scoped isolation)."""

    def test_create_tenant_minimal(self):
        """Create a tenant with required fields only."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/tenants",
            json={
                "name": "Acme Corporation",
                "subdomain": "acme",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Acme Corporation"
        assert data["subdomain"] == "acme"
        assert data["tier"] == "shared"
        assert data["status"] == "pending"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_tenant_with_all_fields(self):
        """Create a tenant with all optional fields."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/tenants",
            json={
                "name": "Premium Corp",
                "subdomain": "premium",
                "custom_domain": "premium.myapp.com",
                "tier": "dedicated",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Premium Corp"
        assert data["custom_domain"] == "premium.myapp.com"
        assert data["tier"] == "dedicated"
        assert data["status"] == "pending"  # Default status

    def test_get_tenant(self):
        """Retrieve a tenant."""
        client = TestClient(app)
        
        create_response = client.post(
            "/api/v1/tenants",
            json={
                "name": "Test Org",
                "subdomain": "testorg",
            },
        )
        
        tenant_id = create_response.json()["id"]
        
        get_response = client.get(f"/api/v1/tenants/{tenant_id}")
        
        assert get_response.status_code == 200
        assert get_response.json()["id"] == tenant_id
        assert get_response.json()["name"] == "Test Org"

    def test_update_tenant(self):
        """Update a tenant."""
        client = TestClient(app)
        
        create_response = client.post(
            "/api/v1/tenants",
            json={
                "name": "Original Name",
                "subdomain": "original",
            },
        )
        
        tenant_id = create_response.json()["id"]
        
        update_response = client.patch(
            f"/api/v1/tenants/{tenant_id}",
            json={"name": "Updated Name", "status": "active"},
        )
        
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Name"
        assert update_response.json()["status"] == "active"

    def test_delete_tenant(self):
        """Delete a tenant."""
        client = TestClient(app)
        
        create_response = client.post(
            "/api/v1/tenants",
            json={
                "name": "Temp Org",
                "subdomain": "temporg",
            },
        )
        
        tenant_id = create_response.json()["id"]
        
        delete_response = client.delete(f"/api/v1/tenants/{tenant_id}")
        
        assert delete_response.status_code == 204
        
        get_response = client.get(f"/api/v1/tenants/{tenant_id}")
        assert get_response.status_code == 404

    def test_list_tenants(self):
        """List all tenants."""
        client = TestClient(app)
        
        for i in range(3):
            client.post(
                "/api/v1/tenants",
                json={
                    "name": f"Tenant {i}",
                    "subdomain": f"tenant{i}",
                },
            )
        
        list_response = client.get("/api/v1/tenants")
        
        assert list_response.status_code == 200
        assert len(list_response.json()) == 3


class TestTenantSchema:
    """Test tenant schema validation."""

    def test_tenant_invalid_tier(self):
        """Verify invalid tier is rejected."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/tenants",
            json={
                "name": "Test",
                "subdomain": "test",
                "tier": "invalid_tier",
            },
        )
        
        assert response.status_code >= 400

    def test_tenant_invalid_status(self):
        """Verify invalid status is rejected on update."""
        client = TestClient(app)
        
        create_response = client.post(
            "/api/v1/tenants",
            json={
                "name": "Test",
                "subdomain": "test",
            },
        )
        
        tenant_id = create_response.json()["id"]
        
        response = client.patch(
            f"/api/v1/tenants/{tenant_id}",
            json={"status": "invalid_status"},
        )
        
        assert response.status_code >= 400

    def test_tenant_missing_required_field(self):
        """Verify missing required field is rejected."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/tenants",
            json={
                "name": "Test",
            },
        )
        
        assert response.status_code >= 400

    def test_tenant_empty_name(self):
        """Verify empty name is accepted (no validation)."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/tenants",
            json={
                "name": "",
                "subdomain": "test",
            },
        )
        
        # No validation on empty name
        assert response.status_code == 201

    def test_tenant_empty_subdomain(self):
        """Verify empty subdomain is accepted (no validation)."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/tenants",
            json={
                "name": "Test",
                "subdomain": "",
            },
        )
        
        # No validation on empty subdomain
        assert response.status_code == 201


class TestTenantEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_get_nonexistent_tenant(self):
        """Verify getting nonexistent tenant returns 404."""
        client = TestClient(app)
        
        response = client.get(f"/api/v1/tenants/{uuid4()}")
        
        assert response.status_code == 404

    def test_update_nonexistent_tenant(self):
        """Verify updating nonexistent tenant returns 404."""
        client = TestClient(app)
        
        response = client.patch(
            f"/api/v1/tenants/{uuid4()}",
            json={"name": "Updated"},
        )
        
        assert response.status_code == 404

    def test_delete_nonexistent_tenant(self):
        """Verify deleting nonexistent tenant returns 404."""
        client = TestClient(app)
        
        response = client.delete(f"/api/v1/tenants/{uuid4()}")
        
        assert response.status_code == 404

    def test_tenant_tier_enum(self):
        """Verify all tenant tiers work."""
        client = TestClient(app)
        
        for tier in ["shared", "dedicated"]:
            response = client.post(
                "/api/v1/tenants",
                json={
                    "name": f"Tenant {tier}",
                    "subdomain": f"tenant{tier}",
                    "tier": tier,
                },
            )
            assert response.status_code == 201
            assert response.json()["tier"] == tier

    def test_tenant_status_enum(self):
        """Verify all tenant statuses work (via update)."""
        client = TestClient(app)
        
        for status in ["pending", "active", "suspended"]:
            # Create with default status
            create_response = client.post(
                "/api/v1/tenants",
                json={
                    "name": f"Tenant {status}",
                    "subdomain": f"tenant{status}",
                },
            )
            assert create_response.status_code == 201
            
            tenant_id = create_response.json()["id"]
            
            # Update to target status
            update_response = client.patch(
                f"/api/v1/tenants/{tenant_id}",
                json={"status": status},
            )
            assert update_response.status_code == 200
            assert update_response.json()["status"] == status

    def test_tenant_duplicate_subdomain(self):
        """Verify duplicate subdomain handling."""
        client = TestClient(app)
        
        response1 = client.post(
            "/api/v1/tenants",
            json={
                "name": "First",
                "subdomain": "shared-subdomain",
            },
        )
        
        assert response1.status_code == 201
        
        response2 = client.post(
            "/api/v1/tenants",
            json={
                "name": "Second",
                "subdomain": "shared-subdomain",
            },
        )
        
        assert response2.status_code == 201

    def test_tenant_update_preserves_id(self):
        """Verify updating tenant preserves ID."""
        client = TestClient(app)
        
        create_response = client.post(
            "/api/v1/tenants",
            json={
                "name": "Original",
                "subdomain": "original",
            },
        )
        
        tenant_id = create_response.json()["id"]
        
        update_response = client.patch(
            f"/api/v1/tenants/{tenant_id}",
            json={"name": "Updated"},
        )
        
        assert update_response.json()["id"] == tenant_id

    def test_tenant_list_empty(self):
        """Verify listing empty tenant directory returns empty list."""
        client = TestClient(app)
        
        list_response = client.get("/api/v1/tenants")
        
        assert list_response.status_code == 200
        assert list_response.json() == []

    def test_tenant_long_name(self):
        """Verify long tenant name is accepted."""
        client = TestClient(app)
        
        long_name = "A" * 500
        
        response = client.post(
            "/api/v1/tenants",
            json={
                "name": long_name,
                "subdomain": "test",
            },
        )
        
        assert response.status_code == 201
        assert response.json()["name"] == long_name

    def test_tenant_special_characters_in_fields(self):
        """Verify special characters are handled."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/tenants",
            json={
                "name": "ABC Corp & Co., Ltd.",
                "subdomain": "abc-corp",
                "custom_domain": "abc.example.com",
            },
        )
        
        assert response.status_code == 201
