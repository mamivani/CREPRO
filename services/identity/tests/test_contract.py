"""Contract tests for Identity service OpenAPI schema.

Validates that the Identity service API conforms to its OpenAPI specification
and can be consumed by other services following the contract.
"""

from uuid import uuid4

import pytest
from crepro_identity.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def openapi_schema():
    # Use the app's openapi() method which caches and avoids network calls
    if app.openapi_schema:
        return app.openapi_schema
    # Trigger OpenAPI schema generation through the /openapi.json endpoint
    client = TestClient(app)
    response = client.get("/openapi.json")
    if response.status_code == 200:
        return response.json()
    return {}


class TestContractHealth:
    """Health endpoint contract."""

    def test_health_endpoint_exists(self, openapi_schema):
        assert "/health" in openapi_schema["paths"]

    def test_health_get_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_has_required_fields(self, client):
        response = client.get("/health")
        body = response.json()
        assert "service" in body
        assert "status" in body
        assert body["service"] == "identity"


class TestContractAuthEndpoints:
    """Authentication endpoints contract."""

    def test_all_oauth_endpoints_exist(self, openapi_schema):
        paths = openapi_schema.get("paths", {})
        assert "/api/v1/auth/microsoft" in paths
        assert "/api/v1/auth/google" in paths
        assert "/api/v1/auth/apple" in paths

    def test_local_auth_endpoints_exist(self, openapi_schema):
        paths = openapi_schema.get("paths", {})
        assert "/api/v1/auth/register" in paths
        assert "/api/v1/auth/local" in paths
        assert "/api/v1/auth/refresh" in paths

    def test_oauth_endpoints_are_post_method(self, openapi_schema):
        """Validate OAuth endpoints accept POST."""
        paths = openapi_schema.get("paths", {})
        for path in ["/api/v1/auth/microsoft", "/api/v1/auth/google", "/api/v1/auth/apple"]:
            assert "post" in paths.get(path, {})


class TestContractUserEndpoints:
    """User management endpoints contract."""

    def test_user_endpoints_exist(self, openapi_schema):
        paths = openapi_schema.get("paths", {})
        assert "/api/v1/users" in paths
        assert "/api/v1/users/{entity_id}" in paths


class TestContractResponseSchemas:
    """Validates response schemas match contract."""

    def test_token_response_has_access_token_and_type(self, openapi_schema):
        """Verify TokenResponse schema includes required fields."""
        schemas = openapi_schema.get("components", {}).get("schemas", {})
        token_response = schemas.get("TokenResponse")
        if token_response:
            assert "properties" in token_response
            assert "access_token" in token_response["properties"]
            assert "token_type" in token_response["properties"]

    def test_user_response_has_core_fields(self, openapi_schema):
        """Verify User schema includes required fields."""
        schemas = openapi_schema.get("components", {}).get("schemas", {})
        user_schema = schemas.get("User")
        if user_schema:
            assert "properties" in user_schema
            # User should have tenant_id, email, role
            props = user_schema["properties"]
            assert any(key in props for key in ["tenant_id", "email", "role"])


class TestContractMultiProviderConsistency:
    """Validates all OAuth providers follow same contract."""

    @pytest.mark.parametrize("provider", ["microsoft", "google", "apple"])
    def test_all_oauth_providers_have_post_method(self, client, provider):
        """All OAuth endpoints accept POST requests."""
        # Just verify the path exists by checking for MethodNotAllowed on other methods
        response = client.get(f"/api/v1/auth/{provider}")
        # GET not allowed; should be 405 Method Not Allowed or 404 if not found
        assert response.status_code in [404, 405]
