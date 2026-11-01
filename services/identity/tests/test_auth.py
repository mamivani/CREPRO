"""Tests for authentication endpoints."""

import pytest
from uuid import UUID

from crepro_identity.main import app
from crepro_identity.models import User, UserStatus
from crepro_identity.repository import users
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def clear_users():
    """Clear users repository before each test."""
    users._rows.clear()
    yield
    users._rows.clear()


client = TestClient(app)


def test_local_auth_with_valid_credentials():
    """Test local authentication with valid email/password."""
    # Setup: create a test user
    test_user = User(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        tenant_id=UUID("22222222-2222-2222-2222-222222222222"),
        email="test@example.com",
        full_name="Test User",
        role="property_manager",
        status=UserStatus.ACTIVE,
    )
    users._rows[test_user.id] = test_user

    # Test login
    response = client.post(
        "/api/v1/auth/local",
        json={
            "email": "test@example.com",
            "password": "any-password",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert "expires_in" in data
    assert data["access_token"]


def test_local_auth_with_invalid_email():
    """Test local authentication with non-existent email."""
    response = client.post(
        "/api/v1/auth/local",
        json={
            "email": "nonexistent@example.com",
            "password": "any-password",
        },
    )

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_local_auth_with_disabled_user():
    """Test local authentication with disabled user account."""
    test_user = User(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        tenant_id=UUID("22222222-2222-2222-2222-222222222222"),
        email="disabled@example.com",
        full_name="Disabled User",
        role="property_manager",
        status=UserStatus.DISABLED,
    )
    users._rows[test_user.id] = test_user

    response = client.post(
        "/api/v1/auth/local",
        json={
            "email": "disabled@example.com",
            "password": "any-password",
        },
    )

    assert response.status_code == 401
    assert "disabled" in response.json()["detail"]


def test_microsoft_auth_returns_jwt_with_tenant():
    """Test Microsoft OAuth login returns JWT with tenant context."""
    response = client.post(
        "/api/v1/auth/microsoft",
        params={
            "code": "test-auth-code",
            "redirect_uri": "http://localhost:3000/callback",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"

    # Decode token to verify claims
    from crepro_identity.auth_service import auth_service

    claims = auth_service.validate_token(data["access_token"])
    assert claims.sub == "11111111-1111-1111-1111-111111111111"
    assert claims.tenant_id == "22222222-2222-2222-2222-222222222222"
    assert claims.role == "property_manager"


def test_google_auth_returns_jwt_with_tenant():
    """Test Google OAuth login returns JWT with tenant context."""
    response = client.post(
        "/api/v1/auth/google",
        params={
            "code": "test-auth-code",
            "redirect_uri": "http://localhost:3000/callback",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"

    from crepro_identity.auth_service import auth_service

    claims = auth_service.validate_token(data["access_token"])
    assert claims.sub == "33333333-3333-3333-3333-333333333333"
    assert claims.tenant_id == "44444444-4444-4444-4444-444444444444"


def test_apple_auth_returns_jwt_with_tenant():
    """Test Apple Sign-In login returns JWT with tenant context."""
    response = client.post(
        "/api/v1/auth/apple",
        params={
            "code": "test-auth-code",
            "redirect_uri": "http://localhost:3000/callback",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"

    from crepro_identity.auth_service import auth_service

    claims = auth_service.validate_token(data["access_token"])
    assert claims.sub == "55555555-5555-5555-5555-555555555555"
    assert claims.tenant_id == "66666666-6666-6666-6666-666666666666"


def test_refresh_token_returns_new_access_token():
    """Test refresh token endpoint returns new access token."""
    # First get an access token
    response = client.post(
        "/api/v1/auth/microsoft",
        params={
            "code": "test-auth-code",
            "redirect_uri": "http://localhost:3000/callback",
        },
    )
    old_token = response.json()["access_token"]

    # Then refresh it
    response = client.post(
        "/api/v1/auth/refresh",
        params={"current_token": old_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"


def test_jwt_token_validation():
    """Test JWT token validation rejects invalid tokens."""
    from crepro_identity.auth_service import auth_service

    invalid_token = "invalid.token.here"
    with pytest.raises(Exception):
        auth_service.validate_token(invalid_token)


def test_jwt_contains_required_claims():
    """Test JWT token contains all required claims."""
    response = client.post(
        "/api/v1/auth/microsoft",
        params={
            "code": "test-auth-code",
            "redirect_uri": "http://localhost:3000/callback",
        },
    )

    from crepro_identity.auth_service import auth_service

    token = response.json()["access_token"]
    claims = auth_service.validate_token(token)

    # Verify all required claims are present
    assert hasattr(claims, "sub")  # userId
    assert hasattr(claims, "tenant_id")
    assert hasattr(claims, "role")
    assert hasattr(claims, "iss")
    assert hasattr(claims, "aud")
    assert hasattr(claims, "iat")
    assert hasattr(claims, "exp")
