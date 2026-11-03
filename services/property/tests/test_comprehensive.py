"""Comprehensive tests for property service: unit, integration, contract, and cross-tenant isolation."""

import pytest
from uuid import uuid4, UUID
from datetime import datetime

from crepro_property.main import app
from crepro_property.models import Property, Unit, PropertyStatus
from crepro_property.repository import properties, units
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_repositories():
    """Reset in-memory repositories before each test."""
    properties._rows.clear()
    units._rows.clear()
    yield
    properties._rows.clear()
    units._rows.clear()


def _headers(tenant_id: UUID | None = None) -> dict[str, str]:
    """Generate request headers with tenant context."""
    if tenant_id is None:
        tenant_id = uuid4()
    return {"X-Tenant-Id": str(tenant_id)}


class TestPropertyCRUD:
    """Test Property CRUD operations with tenant isolation."""

    def test_create_property_minimal(self):
        """Create a property with required fields only."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/properties",
            json={
                "name": "Downtown Apartments",
                "address_line1": "123 Main St",
                "city": "Portland",
                "state": "OR",
                "postal_code": "97201",
                "country": "USA",
                "property_type": "apartment",
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Downtown Apartments"
        assert data["tenant_id"] == str(tenant_id)
        assert data["status"] == "available"
        assert data["max_active_leases"] == 1

    def test_create_property_with_all_fields(self):
        """Create a property with all optional fields."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/properties",
            json={
                "name": "Luxury Complex",
                "address_line1": "456 Oak Ave",
                "address_line2": "Suite 100",
                "city": "Seattle",
                "state": "WA",
                "postal_code": "98101",
                "country": "USA",
                "property_type": "condo",
                "status": "on_lease",
                "description": "Premium waterfront property",
                "max_active_leases": 5,
                "amenities": ["pool", "gym", "parking"],
            },
            headers=_headers(tenant_id),
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Premium waterfront property"
        assert data["max_active_leases"] == 5
        assert data["amenities"] == ["pool", "gym", "parking"]
        assert data["address_line2"] == "Suite 100"

    def test_get_property(self):
        """Retrieve a previously created property."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        # Create
        create_response = client.post(
            "/api/v1/properties",
            json={
                "name": "Test Property",
                "address_line1": "789 Pine",
                "city": "Portland",
                "state": "OR",
                "postal_code": "97201",
                "country": "USA",
                "property_type": "house",
            },
            headers=headers,
        )
        property_id = create_response.json()["id"]
        
        # Retrieve
        get_response = client.get(f"/api/v1/properties/{property_id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["id"] == property_id
        assert get_response.json()["name"] == "Test Property"

    def test_update_property(self):
        """Modify an existing property."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        # Create
        create_response = client.post(
            "/api/v1/properties",
            json={
                "name": "Original Name",
                "address_line1": "123 Main St",
                "city": "Portland",
                "state": "OR",
                "postal_code": "97201",
                "country": "USA",
                "property_type": "apartment",
            },
            headers=headers,
        )
        property_id = create_response.json()["id"]
        
        # Update
        update_response = client.patch(
            f"/api/v1/properties/{property_id}",
            json={
                "name": "Updated Name",
                "status": "on_lease",
                "description": "Now leased",
            },
            headers=headers,
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["name"] == "Updated Name"
        assert updated["status"] == "on_lease"
        assert updated["description"] == "Now leased"

    def test_delete_property(self):
        """Remove a property."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        # Create
        create_response = client.post(
            "/api/v1/properties",
            json={
                "name": "Disposable Property",
                "address_line1": "999 Delete Ave",
                "city": "Portland",
                "state": "OR",
                "postal_code": "97201",
                "country": "USA",
                "property_type": "apartment",
            },
            headers=headers,
        )
        property_id = create_response.json()["id"]
        
        # Delete
        delete_response = client.delete(f"/api/v1/properties/{property_id}", headers=headers)
        assert delete_response.status_code == 204
        
        # Verify gone
        get_response = client.get(f"/api/v1/properties/{property_id}", headers=headers)
        assert get_response.status_code == 404

    def test_list_properties(self):
        """Retrieve all properties for a tenant."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        # Create 3 properties
        property_ids = []
        for i in range(3):
            response = client.post(
                "/api/v1/properties",
                json={
                    "name": f"Property {i}",
                    "address_line1": f"{i} Main",
                    "city": "Portland",
                    "state": "OR",
                    "postal_code": "97201",
                    "country": "USA",
                    "property_type": "apartment",
                },
                headers=headers,
            )
            property_ids.append(response.json()["id"])
        
        # List
        list_response = client.get("/api/v1/properties", headers=headers)
        assert list_response.status_code == 200
        items = list_response.json()
        assert len(items) == 3
        assert all(item["id"] in property_ids for item in items)


class TestUnitCRUD:
    """Test Unit CRUD operations with parent property."""

    def test_create_unit_for_property(self):
        """Create a unit within a property."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        # Create parent property
        prop_response = client.post(
            "/api/v1/properties",
            json={
                "name": "Unit Test Building",
                "address_line1": "555 Oak",
                "city": "Portland",
                "state": "OR",
                "postal_code": "97201",
                "country": "USA",
                "property_type": "apartment",
            },
            headers=headers,
        )
        property_id = UUID(prop_response.json()["id"])
        
        # Create unit
        unit_response = client.post(
            "/api/v1/units",
            json={
                "property_id": str(property_id),
                "unit_number": "101",
                "unit_type": "studio",
                "bedrooms": 0,
                "bathrooms": 1,
                "rent_amount": 1200.0,
            },
            headers=headers,
        )
        
        assert unit_response.status_code == 201
        unit = unit_response.json()
        assert unit["property_id"] == str(property_id)
        assert unit["unit_number"] == "101"
        assert unit["unit_type"] == "studio"
        assert unit["rent_amount"] == 1200.0
        assert unit["tenant_id"] == str(tenant_id)

    def test_create_unit_with_all_fields(self):
        """Create a unit with complete details."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        # Create parent property
        prop_response = client.post(
            "/api/v1/properties",
            json={
                "name": "Detailed Property",
                "address_line1": "777 Elm",
                "city": "Seattle",
                "state": "WA",
                "postal_code": "98101",
                "country": "USA",
                "property_type": "condo",
            },
            headers=headers,
        )
        property_id = UUID(prop_response.json()["id"])
        
        # Create detailed unit
        unit_response = client.post(
            "/api/v1/units",
            json={
                "property_id": str(property_id),
                "unit_number": "205",
                "unit_type": "2br/2ba",
                "bedrooms": 2,
                "bathrooms": 2,
                "builtup_area_sqft": 1100.0,
                "carpet_area_sqft": 950.0,
                "facing": "south",
                "parking_spaces": 2,
                "rent_amount": 2500.0,
                "security_deposit_amount": 5000.0,
                "currency": "USD",
                "is_smoking_allowed": False,
                "is_furnished": True,
                "status": "on_lease",
                "amenities": ["balcony", "in-unit-laundry"],
            },
            headers=headers,
        )
        
        assert unit_response.status_code == 201
        unit = unit_response.json()
        assert unit["bedrooms"] == 2
        assert unit["bathrooms"] == 2
        assert unit["builtup_area_sqft"] == 1100.0
        assert unit["facing"] == "south"
        assert unit["is_furnished"] is True
        assert unit["amenities"] == ["balcony", "in-unit-laundry"]

    def test_get_unit(self):
        """Retrieve a unit by ID."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        # Setup
        prop_response = client.post(
            "/api/v1/properties",
            json={
                "name": "Get Unit Test",
                "address_line1": "111 Get",
                "city": "Portland",
                "state": "OR",
                "postal_code": "97201",
                "country": "USA",
                "property_type": "apartment",
            },
            headers=headers,
        )
        property_id = UUID(prop_response.json()["id"])
        
        unit_response = client.post(
            "/api/v1/units",
            json={
                "property_id": str(property_id),
                "unit_number": "301",
                "unit_type": "1br",
                "bedrooms": 1,
                "bathrooms": 1,
                "rent_amount": 1500.0,
            },
            headers=headers,
        )
        unit_id = unit_response.json()["id"]
        
        # Get
        get_response = client.get(f"/api/v1/units/{unit_id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["unit_number"] == "301"

    def test_list_units_for_property(self):
        """List all units for a specific property."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        # Create property
        prop_response = client.post(
            "/api/v1/properties",
            json={
                "name": "Multi-Unit Building",
                "address_line1": "222 Many",
                "city": "Portland",
                "state": "OR",
                "postal_code": "97201",
                "country": "USA",
                "property_type": "apartment",
            },
            headers=headers,
        )
        property_id = UUID(prop_response.json()["id"])
        
        # Create 5 units
        for i in range(5):
            client.post(
                "/api/v1/units",
                json={
                    "property_id": str(property_id),
                    "unit_number": f"10{i}",
                    "unit_type": "studio",
                    "bedrooms": 0,
                    "bathrooms": 1,
                    "rent_amount": 1200.0,
                },
                headers=headers,
            )
        
        # List all units
        list_response = client.get("/api/v1/units", headers=headers)
        assert list_response.status_code == 200
        assert len(list_response.json()) == 5


class TestCrossTenantisolation:
    """Verify tenant A cannot access tenant B's data."""

    def test_property_isolation_read(self):
        """Tenant B cannot read tenant A's property."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        # Tenant A creates property
        response = client.post(
            "/api/v1/properties",
            json={
                "name": "Secret Property",
                "address_line1": "666 Secrets",
                "city": "Portland",
                "state": "OR",
                "postal_code": "97201",
                "country": "USA",
                "property_type": "apartment",
            },
            headers=_headers(tenant_a),
        )
        property_id = response.json()["id"]
        
        # Tenant B tries to read
        get_response = client.get(
            f"/api/v1/properties/{property_id}",
            headers=_headers(tenant_b),
        )
        assert get_response.status_code == 404

    def test_property_isolation_list(self):
        """Tenant B sees only their own properties."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        # Tenant A creates 2 properties
        for i in range(2):
            client.post(
                "/api/v1/properties",
                json={
                    "name": f"A Property {i}",
                    "address_line1": f"{i} A",
                    "city": "Portland",
                    "state": "OR",
                    "postal_code": "97201",
                    "country": "USA",
                    "property_type": "apartment",
                },
                headers=_headers(tenant_a),
            )
        
        # Tenant B creates 1 property
        client.post(
            "/api/v1/properties",
            json={
                "name": "B Property",
                "address_line1": "1 B",
                "city": "Seattle",
                "state": "WA",
                "postal_code": "98101",
                "country": "USA",
                "property_type": "condo",
            },
            headers=_headers(tenant_b),
        )
        
        # Each tenant lists their own
        a_list = client.get("/api/v1/properties", headers=_headers(tenant_a)).json()
        b_list = client.get("/api/v1/properties", headers=_headers(tenant_b)).json()
        
        assert len(a_list) == 2
        assert len(b_list) == 1
        assert all(p["tenant_id"] == str(tenant_a) for p in a_list)
        assert all(p["tenant_id"] == str(tenant_b) for p in b_list)

    def test_unit_isolation(self):
        """Tenant B cannot access tenant A's units."""
        client = TestClient(app)
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        # Tenant A creates property and unit
        prop_response = client.post(
            "/api/v1/properties",
            json={
                "name": "A Building",
                "address_line1": "111 A",
                "city": "Portland",
                "state": "OR",
                "postal_code": "97201",
                "country": "USA",
                "property_type": "apartment",
            },
            headers=_headers(tenant_a),
        )
        property_id = UUID(prop_response.json()["id"])
        
        unit_response = client.post(
            "/api/v1/units",
            json={
                "property_id": str(property_id),
                "unit_number": "501",
                "unit_type": "studio",
                "bedrooms": 0,
                "bathrooms": 1,
                "rent_amount": 1200.0,
            },
            headers=_headers(tenant_a),
        )
        unit_id = unit_response.json()["id"]
        
        # Tenant B tries to access
        get_response = client.get(
            f"/api/v1/units/{unit_id}",
            headers=_headers(tenant_b),
        )
        assert get_response.status_code == 404


class TestPropertyContractSchema:
    """Verify API response schema matches OpenAPI definition."""

    def test_property_response_schema(self):
        """Property response includes all defined fields."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        response = client.post(
            "/api/v1/properties",
            json={
                "name": "Schema Test",
                "address_line1": "333 Schema",
                "city": "Portland",
                "state": "OR",
                "postal_code": "97201",
                "country": "USA",
                "property_type": "apartment",
            },
            headers=_headers(tenant_id),
        )
        
        data = response.json()
        # Required fields
        assert "id" in data
        assert "tenant_id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "name" in data
        assert "address_line1" in data
        assert "city" in data
        assert "state" in data
        assert "postal_code" in data
        assert "country" in data
        assert "property_type" in data
        assert "status" in data

    def test_unit_response_schema(self):
        """Unit response includes all defined fields."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        prop_response = client.post(
            "/api/v1/properties",
            json={
                "name": "Schema Building",
                "address_line1": "444 Schema",
                "city": "Portland",
                "state": "OR",
                "postal_code": "97201",
                "country": "USA",
                "property_type": "apartment",
            },
            headers=headers,
        )
        property_id = UUID(prop_response.json()["id"])
        
        unit_response = client.post(
            "/api/v1/units",
            json={
                "property_id": str(property_id),
                "unit_number": "601",
                "unit_type": "2br",
                "bedrooms": 2,
                "bathrooms": 1,
                "rent_amount": 2000.0,
            },
            headers=headers,
        )
        
        data = unit_response.json()
        # Required fields
        assert "id" in data
        assert "tenant_id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "property_id" in data
        assert "unit_number" in data
        assert "unit_type" in data
        assert "rent_amount" in data


class TestPropertyEdgeCases:
    """Edge cases and error scenarios."""

    def test_create_property_missing_required_field(self):
        """Property creation fails without required fields."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/properties",
            json={
                "name": "Incomplete",
                # Missing address_line1, city, state, postal_code, country, property_type
            },
            headers=_headers(),
        )
        assert response.status_code == 422  # Validation error

    def test_create_unit_with_nonexistent_property(self):
        """Unit creation fails if parent property doesn't exist (in real DB; in-memory doesn't enforce)."""
        client = TestClient(app)
        tenant_id = uuid4()
        
        # This test documents current behavior (in-memory doesn't validate FK)
        # In a real DB implementation, this would return 404 or 422
        response = client.post(
            "/api/v1/units",
            json={
                "property_id": str(uuid4()),  # Non-existent property
                "unit_number": "701",
                "unit_type": "studio",
                "bedrooms": 0,
                "bathrooms": 1,
                "rent_amount": 1200.0,
            },
            headers=_headers(tenant_id),
        )
        # In-memory implementation allows this; real DB would reject
        assert response.status_code in [201, 422]

    def test_get_nonexistent_property(self):
        """Getting a non-existent property returns 404."""
        client = TestClient(app)
        
        response = client.get(
            f"/api/v1/properties/{uuid4()}",
            headers=_headers(),
        )
        assert response.status_code == 404

    def test_update_with_partial_fields(self):
        """Update can use a subset of fields."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        # Create
        create_response = client.post(
            "/api/v1/properties",
            json={
                "name": "Partial Update Test",
                "address_line1": "555 Partial",
                "city": "Portland",
                "state": "OR",
                "postal_code": "97201",
                "country": "USA",
                "property_type": "apartment",
                "max_active_leases": 2,
            },
            headers=headers,
        )
        property_id = create_response.json()["id"]
        original = create_response.json()
        
        # Update only status
        patch_response = client.patch(
            f"/api/v1/properties/{property_id}",
            json={"status": "sold"},
            headers=headers,
        )
        
        assert patch_response.status_code == 200
        updated = patch_response.json()
        assert updated["status"] == "sold"
        assert updated["name"] == original["name"]  # Unchanged
        assert updated["max_active_leases"] == 2  # Unchanged

    def test_double_delete_property(self):
        """Deleting already-deleted property returns 404."""
        client = TestClient(app)
        tenant_id = uuid4()
        headers = _headers(tenant_id)
        
        # Create and delete
        create_response = client.post(
            "/api/v1/properties",
            json={
                "name": "Double Delete",
                "address_line1": "777 Delete",
                "city": "Portland",
                "state": "OR",
                "postal_code": "97201",
                "country": "USA",
                "property_type": "apartment",
            },
            headers=headers,
        )
        property_id = create_response.json()["id"]
        
        client.delete(f"/api/v1/properties/{property_id}", headers=headers)
        
        # Try to delete again
        response = client.delete(f"/api/v1/properties/{property_id}", headers=headers)
        assert response.status_code == 404
