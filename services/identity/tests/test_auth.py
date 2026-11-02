from uuid import uuid4

import pytest
from crepro_common import TokenType, decode_token, issue_token_pair
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


class _UnresolvableDirectory:
    def resolve_by_host(self, host: str):
        return None


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


@pytest.mark.parametrize("provider_dep", [get_microsoft_provider, get_google_provider, get_apple_provider])
def test_oauth_login_paths_each_return_a_jwt_with_tenant_context(client, tenant_id, provider_dep) -> None:
    _stub_directory(tenant_id)
    app.dependency_overrides[provider_dep] = lambda: _FakeProvider(
        identity=ExternalIdentity(subject="ext-123", email="pat@example.com", full_name="Pat Manager")
    )
    path = {
        get_microsoft_provider: "microsoft",
        get_google_provider: "google",
        get_apple_provider: "apple",
    }[provider_dep]

    response = client.post(f"/api/v1/auth/{path}", json={"id_token": "fake-token"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"

    claims = decode_token(body["access_token"], expected_type=TokenType.ACCESS)
    assert claims.tenant_id == tenant_id
    assert claims.role == "property_manager"


def test_oauth_login_reuses_existing_user_on_repeat_login(client, tenant_id) -> None:
    _stub_directory(tenant_id)
    app.dependency_overrides[get_microsoft_provider] = lambda: _FakeProvider(
        identity=ExternalIdentity(subject="ext-456", email="repeat@example.com", full_name="Repeat User")
    )

    first = client.post("/api/v1/auth/microsoft", json={"id_token": "t1"})
    second = client.post("/api/v1/auth/microsoft", json={"id_token": "t2"})

    first_claims = decode_token(first.json()["access_token"], expected_type=TokenType.ACCESS)
    second_claims = decode_token(second.json()["access_token"], expected_type=TokenType.ACCESS)
    assert first_claims.user_id == second_claims.user_id


def test_oauth_login_rejects_invalid_id_token(client, tenant_id) -> None:
    _stub_directory(tenant_id)
    app.dependency_overrides[get_google_provider] = lambda: _FakeProvider(
        error="signature verification failed"
    )

    response = client.post("/api/v1/auth/google", json={"id_token": "bad"})

    assert response.status_code == 401


def test_oauth_login_without_resolvable_tenant_returns_400(client) -> None:
    app.dependency_overrides[get_tenant_directory] = lambda: _UnresolvableDirectory()
    app.dependency_overrides[get_microsoft_provider] = lambda: _FakeProvider(
        identity=ExternalIdentity(subject="ext-789", email="nowhere@example.com", full_name="No Tenant")
    )

    response = client.post("/api/v1/auth/microsoft", json={"id_token": "t"})

    assert response.status_code == 400


def test_local_register_then_login_returns_a_jwt(client, tenant_id) -> None:
    _stub_directory(tenant_id)

    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "local@example.com", "full_name": "Local User", "password": "correct horse battery"},
    )
    assert registered.status_code == 201

    logged_in = client.post(
        "/api/v1/auth/local", json={"email": "local@example.com", "password": "correct horse battery"}
    )

    assert logged_in.status_code == 200

    claims = decode_token(logged_in.json()["access_token"], expected_type=TokenType.ACCESS)
    assert claims.tenant_id == tenant_id


def test_local_register_rejects_duplicate_email_for_same_tenant(client, tenant_id) -> None:
    _stub_directory(tenant_id)
    payload = {"email": "dup@example.com", "full_name": "Dup User", "password": "hunter2hunter2"}

    client.post("/api/v1/auth/register", json=payload)
    second = client.post("/api/v1/auth/register", json=payload)

    assert second.status_code == 409


def test_local_login_rejects_wrong_password(client, tenant_id) -> None:
    _stub_directory(tenant_id)
    client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpw@example.com", "full_name": "Wrong Pw", "password": "the-real-password"},
    )

    response = client.post(
        "/api/v1/auth/local", json={"email": "wrongpw@example.com", "password": "not-the-password"}
    )

    assert response.status_code == 401


def test_local_login_rejects_unknown_email(client, tenant_id) -> None:
    _stub_directory(tenant_id)

    response = client.post(
        "/api/v1/auth/local", json={"email": "ghost@example.com", "password": "whatever123"}
    )

    assert response.status_code == 401


def test_refresh_returns_a_new_token_pair(client, tenant_id) -> None:
    _stub_directory(tenant_id)
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "full_name": "Refresh User", "password": "super-secret-pw"},
    )
    refresh_token = registered.json()["refresh_token"]

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert refreshed.status_code == 200
    refreshed_claims = decode_token(refreshed.json()["access_token"], expected_type=TokenType.ACCESS)
    original_claims = decode_token(registered.json()["access_token"], expected_type=TokenType.ACCESS)
    assert refreshed_claims.user_id == original_claims.user_id
    assert refreshed_claims.tenant_id == original_claims.tenant_id


def test_refresh_rejects_an_access_token(client, tenant_id) -> None:
    _stub_directory(tenant_id)
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "accessnotrefresh@example.com", "full_name": "A B", "password": "super-secret-pw"},
    )
    access_token = registered.json()["access_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})

    assert response.status_code == 401


def test_refresh_rejects_garbage_token(client) -> None:
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-jwt"})

    assert response.status_code == 401


def test_local_login_rejects_disabled_user(client, tenant_id) -> None:
    _stub_directory(tenant_id)
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "disabled@example.com", "full_name": "Disabled User", "password": "super-secret-pw"},
    )
    claims = decode_token(registered.json()["access_token"], expected_type=TokenType.ACCESS)
    client.patch(
        f"/api/v1/users/{claims.user_id}",
        json={"status": "disabled"},
        headers={"X-Tenant-Id": str(tenant_id)},
    )

    response = client.post(
        "/api/v1/auth/local", json={"email": "disabled@example.com", "password": "super-secret-pw"}
    )

    assert response.status_code == 403


def test_refresh_rejects_disabled_user(client, tenant_id) -> None:
    _stub_directory(tenant_id)
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "refreshdisabled@example.com", "full_name": "R D", "password": "super-secret-pw"},
    )
    claims = decode_token(registered.json()["access_token"], expected_type=TokenType.ACCESS)
    client.patch(
        f"/api/v1/users/{claims.user_id}",
        json={"status": "disabled"},
        headers={"X-Tenant-Id": str(tenant_id)},
    )

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": registered.json()["refresh_token"]})

    assert response.status_code == 403


def test_refresh_rejects_token_for_unknown_user(client) -> None:
    _, refresh_token = issue_token_pair(tenant_id=uuid4(), user_id=uuid4(), role="property_manager")

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 401


def test_provider_factories_build_providers_from_settings() -> None:
    assert get_microsoft_provider().name == "microsoft"
    assert get_google_provider().name == "google"
    assert get_apple_provider().name == "apple"
    assert get_tenant_directory() is not None
