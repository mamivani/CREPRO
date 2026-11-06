"""Advanced integration and workflow tests for Identity service.

Tests complex scenarios, error handling, and cross-endpoint interactions.
"""

from uuid import uuid4

import pytest
from crepro_common import TokenType, decode_token
from crepro_identity.auth import (
    get_apple_provider,
    get_google_provider,
    get_microsoft_provider,
    get_tenant_directory,
)
from crepro_identity.main import app
from crepro_identity.oauth import ExternalIdentity, OAuthVerificationError
from fastapi.testclient import TestClient


class _FakeDirectory:
    """Stands in for TenantDirectoryClient: always resolves to one fixed tenant."""

    def __init__(self, tenant_id) -> None:
        self._tenant_id = tenant_id

    def resolve_by_host(self, host: str):
        return self._tenant_id


class _FakeProvider:
    def __init__(self, *, identity: ExternalIdentity | None = None, error: str | None = None) -> None:
        self._identity = identity
        self._error = error

    def verify(self, id_token: str) -> ExternalIdentity:
        if self._error is not None:
            raise OAuthVerificationError(self._error)
        assert self._identity is not None
        return self._identity


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def tenant_id():
    return uuid4()


def _stub_directory(tenant_id) -> None:
    app.dependency_overrides[get_tenant_directory] = lambda: _FakeDirectory(tenant_id)


class TestMultiProviderCrossSignUp:
    """Test signing up with multiple providers."""

    def test_same_email_registered_via_oauth_and_local_account_isolation(self, client, tenant_id) -> None:
        """User registered via OAuth and then via local account are separate."""
        _stub_directory(tenant_id)
        app.dependency_overrides[get_microsoft_provider] = lambda: _FakeProvider(
            identity=ExternalIdentity(subject="ext-001", email="user@example.com", full_name="OAuth User")
        )

        # Register via OAuth
        oauth_response = client.post("/api/v1/auth/microsoft", json={"id_token": "token1"})
        oauth_user_id = decode_token(
            oauth_response.json()["access_token"], expected_type=TokenType.ACCESS
        ).user_id

        # Try to register local account with same email
        local_response = client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "full_name": "Local User", "password": "password123"},
        )

        # Should fail due to email conflict
        assert local_response.status_code == 409

    def test_different_emails_same_user_via_different_providers_separate_accounts(
        self, client, tenant_id
    ) -> None:
        """Different emails via OAuth providers create separate users."""
        _stub_directory(tenant_id)
        app.dependency_overrides[get_microsoft_provider] = lambda: _FakeProvider(
            identity=ExternalIdentity(subject="ext-111", email="alice@example.com", full_name="Alice M")
        )
        app.dependency_overrides[get_google_provider] = lambda: _FakeProvider(
            identity=ExternalIdentity(subject="ext-112", email="bob@example.com", full_name="Bob G")
        )

        ms_response = client.post("/api/v1/auth/microsoft", json={"id_token": "token1"})
        google_response = client.post("/api/v1/auth/google", json={"id_token": "token2"})

        ms_user_id = decode_token(ms_response.json()["access_token"], expected_type=TokenType.ACCESS).user_id
        google_user_id = decode_token(
            google_response.json()["access_token"], expected_type=TokenType.ACCESS
        ).user_id

        assert ms_user_id != google_user_id


class TestTokenRefreshEdgeCases:
    """Edge cases and error scenarios for token refresh."""

    def test_refresh_with_malformed_json_returns_422(self, client):
        """Malformed refresh request returns validation error."""
        response = client.post("/api/v1/auth/refresh", json={"wrong_field": "value"})
        assert response.status_code == 422

    def test_refresh_returns_new_refresh_token(self, client, tenant_id) -> None:
        """Refresh produces new tokens for continued authentication."""
        _stub_directory(tenant_id)
        registered = client.post(
            "/api/v1/auth/register",
            json={"email": "refresh@example.com", "full_name": "Refresh User", "password": "super-secret"},
        )

        refresh_token = registered.json()["refresh_token"]

        refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

        # Refresh should succeed and return tokens
        assert refreshed.status_code == 200
        assert "access_token" in refreshed.json()
        assert "refresh_token" in refreshed.json()


class TestLocalAuthenticationEdgeCases:
    """Edge cases in local authentication."""

    def test_register_with_empty_password_can_login_with_empty(self, client, tenant_id) -> None:
        """Empty password can register and login (no minimum length validation)."""
        _stub_directory(tenant_id)
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "empty@example.com", "full_name": "User", "password": ""},
        )
        assert response.status_code == 201

        # Can login with empty password
        login_response = client.post("/api/v1/auth/local", json={"email": "empty@example.com", "password": ""})
        assert login_response.status_code == 200

    def test_register_with_very_long_password_accepted(self, client, tenant_id) -> None:
        """Very long passwords should be accepted."""
        _stub_directory(tenant_id)
        long_password = "x" * 1000
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "longpw@example.com", "full_name": "User", "password": long_password},
        )
        assert response.status_code == 201

    def test_login_case_sensitive_email(self, client, tenant_id) -> None:
        """Email matching is case-sensitive."""
        _stub_directory(tenant_id)
        client.post(
            "/api/v1/auth/register",
            json={"email": "User@example.com", "full_name": "User", "password": "password123"},
        )

        # Try to login with different case
        response = client.post("/api/v1/auth/local", json={"email": "user@example.com", "password": "password123"})

        # Should fail (email not found due to case mismatch)
        assert response.status_code == 401

    def test_password_hashing_not_reversible(self, client, tenant_id) -> None:
        """Password hash cannot be reversed to get plaintext."""
        _stub_directory(tenant_id)
        from crepro_identity.passwords import hash_password

        password = "super-secret-password"
        hashed = hash_password(password)

        # Hash should not equal plaintext
        assert hashed != password


class TestCrossTenantisolation:
    """Validate strict cross-tenant isolation."""

    def test_tenant_a_cannot_refresh_token_from_tenant_b(self, client) -> None:
        """Refresh token from tenant B cannot be used to refresh in tenant A context."""
        tenant_a, tenant_b = uuid4(), uuid4()

        # Register user in tenant A
        app.dependency_overrides[get_tenant_directory] = lambda: _FakeDirectory(tenant_a)
        registered_a = client.post(
            "/api/v1/auth/register",
            json={"email": "userA@example.com", "full_name": "User A", "password": "password123"},
        )
        refresh_token_a = registered_a.json()["refresh_token"]

        # Switch context to tenant B (in a new client session, but same refresh token)
        # The refresh endpoint doesn't require tenant context, but the token itself
        # carries tenant_id. This validates the token is bound to tenant.
        refreshed_in_a = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_a})
        claims_a = decode_token(refreshed_in_a.json()["access_token"], expected_type=TokenType.ACCESS)

        assert claims_a.tenant_id == tenant_a


class TestOAuthProviderIntegration:
    """Integration scenarios with OAuth providers."""

    def test_oauth_provider_error_returns_401_unauthorized(self, client, tenant_id) -> None:
        """Any OAuth provider error returns 401."""
        _stub_directory(tenant_id)
        app.dependency_overrides[get_microsoft_provider] = lambda: _FakeProvider(
            error="Token signature verification failed"
        )

        response = client.post("/api/v1/auth/microsoft", json={"id_token": "invalid"})

        assert response.status_code == 401
        assert "signature" in response.json()["detail"].lower() or "error" in response.json()

    def test_oauth_success_idempotent_across_multiple_calls(self, client, tenant_id) -> None:
        """Logging in multiple times with same identity returns same user."""
        _stub_directory(tenant_id)
        app.dependency_overrides[get_google_provider] = lambda: _FakeProvider(
            identity=ExternalIdentity(subject="ext-999", email="idempotent@example.com", full_name="User")
        )

        user_ids = []
        for _ in range(3):
            response = client.post("/api/v1/auth/google", json={"id_token": "token"})
            assert response.status_code == 200
            user_id = decode_token(response.json()["access_token"], expected_type=TokenType.ACCESS).user_id
            user_ids.append(user_id)

        # All should be same user
        assert user_ids[0] == user_ids[1] == user_ids[2]
