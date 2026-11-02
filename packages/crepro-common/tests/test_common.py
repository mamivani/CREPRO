from uuid import uuid4

import pytest
from crepro_common import (
    EntityNotFoundError,
    EventEnvelope,
    InMemoryRepository,
    InvalidTokenError,
    Settings,
    TenantContext,
    TenantNotSetError,
    TenantScopedEntity,
    TokenType,
    build_crud_router,
    create_app,
    current_tenant,
    decode_token,
    issue_token_pair,
)
from crepro_common.tenancy import bind_tenant, require_tenant, unbind_tenant
from fastapi import Depends
from fastapi.testclient import TestClient
from pydantic import BaseModel


def test_create_app_exposes_health() -> None:
    client = TestClient(create_app("sample"))
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "sample", "status": "ok"}


def test_current_tenant_requires_binding() -> None:
    with pytest.raises(TenantNotSetError):
        current_tenant()


def test_tenant_binding_round_trip() -> None:
    tenant_id = uuid4()
    token = bind_tenant(TenantContext(tenant_id=tenant_id))
    try:
        assert current_tenant().tenant_id == tenant_id
    finally:
        unbind_tenant(token)


def test_event_envelope_defaults() -> None:
    tenant_id = uuid4()
    event = EventEnvelope(event_type="lease.activated", tenant_id=tenant_id, source="lease")

    assert event.schema_version == 1
    assert event.tenant_id == tenant_id
    assert event.event_id is not None


def test_in_memory_repository_isolates_tenants() -> None:
    repo = InMemoryRepository[TenantScopedEntity]()
    tenant_a, tenant_b = uuid4(), uuid4()
    row_a = repo.create(TenantScopedEntity(tenant_id=tenant_a))
    repo.create(TenantScopedEntity(tenant_id=tenant_b))

    assert [row.id for row in repo.list(tenant_a)] == [row_a.id]
    with pytest.raises(EntityNotFoundError):
        repo.get(tenant_b, row_a.id)


def test_require_tenant_binds_and_unbinds_around_request() -> None:
    app = create_app("sample")

    @app.get("/whoami")
    def whoami(tenant: TenantContext = Depends(require_tenant)) -> dict[str, str]:
        return {"tenant_id": str(tenant.tenant_id)}

    tenant_id = uuid4()
    response = TestClient(app).get("/whoami", headers={"X-Tenant-Id": str(tenant_id)})

    assert response.status_code == 200
    assert response.json()["tenant_id"] == str(tenant_id)
    with pytest.raises(TenantNotSetError):
        current_tenant()


def test_require_tenant_accepts_a_bearer_access_token() -> None:
    app = create_app("sample")

    @app.get("/whoami")
    def whoami(tenant: TenantContext = Depends(require_tenant)) -> dict[str, str]:
        return {"tenant_id": str(tenant.tenant_id)}

    tenant_id = uuid4()
    # No explicit settings: both issuing and require_tenant's decoding fall back to the
    # same cached get_settings(), so this mirrors a real request carrying an identity-issued token.
    access, _ = issue_token_pair(tenant_id=tenant_id, user_id=uuid4(), role="property_manager")

    response = TestClient(app).get("/whoami", headers={"Authorization": f"Bearer {access}"})

    assert response.status_code == 200
    assert response.json()["tenant_id"] == str(tenant_id)


def test_require_tenant_rejects_a_token_with_the_wrong_signature() -> None:
    app = create_app("sample")

    @app.get("/whoami")
    def whoami(tenant: TenantContext = Depends(require_tenant)) -> dict[str, str]:
        return {"tenant_id": str(tenant.tenant_id)}

    access, _ = issue_token_pair(
        tenant_id=uuid4(), user_id=uuid4(), role="property_manager", settings=_settings()
    )

    response = TestClient(app).get("/whoami", headers={"Authorization": f"Bearer {access}"})

    assert response.status_code == 401


def test_require_tenant_rejects_malformed_authorization_header() -> None:
    app = create_app("sample")

    @app.get("/whoami")
    def whoami(tenant: TenantContext = Depends(require_tenant)) -> dict[str, str]:
        return {"tenant_id": str(tenant.tenant_id)}

    response = TestClient(app).get("/whoami", headers={"Authorization": "not-a-bearer-token"})

    assert response.status_code == 401


def test_require_tenant_requires_some_tenant_source() -> None:
    app = create_app("sample")

    @app.get("/whoami")
    def whoami(tenant: TenantContext = Depends(require_tenant)) -> dict[str, str]:
        return {"tenant_id": str(tenant.tenant_id)}

    response = TestClient(app).get("/whoami")

    assert response.status_code == 400


class _Widget(TenantScopedEntity):
    name: str


class _WidgetCreate(BaseModel):
    name: str


class _WidgetUpdate(BaseModel):
    name: str | None = None


def test_build_crud_router_supports_full_lifecycle() -> None:
    repository = InMemoryRepository[_Widget]()
    app = create_app("sample")
    app.include_router(
        build_crud_router(
            prefix="/widgets",
            tags=["widgets"],
            repository=repository,
            entity_cls=_Widget,
            create_schema=_WidgetCreate,
            update_schema=_WidgetUpdate,
            not_found_detail="Widget not found",
        )
    )
    client = TestClient(app)
    headers = {"X-Tenant-Id": str(uuid4())}
    other_tenant_headers = {"X-Tenant-Id": str(uuid4())}

    created = client.post("/widgets", json={"name": "gadget"}, headers=headers)
    assert created.status_code == 201
    widget_id = created.json()["id"]

    assert client.get("/widgets", headers=headers).json()[0]["name"] == "gadget"
    assert client.get(f"/widgets/{widget_id}", headers=other_tenant_headers).status_code == 404

    patched = client.patch(f"/widgets/{widget_id}", json={"name": "renamed"}, headers=headers)
    assert patched.json()["name"] == "renamed"

    assert client.delete(f"/widgets/{widget_id}", headers=headers).status_code == 204
    assert client.get(f"/widgets/{widget_id}", headers=headers).status_code == 404


def _settings() -> Settings:
    return Settings(jwt_secret="test-secret-at-least-32-bytes-long!!", jwt_issuer="crepro-test")


def test_issue_and_decode_access_token_round_trip() -> None:
    settings = _settings()
    tenant_id, user_id = uuid4(), uuid4()
    access, refresh = issue_token_pair(
        tenant_id=tenant_id, user_id=user_id, role="property_manager", settings=settings
    )

    access_claims = decode_token(access, expected_type=TokenType.ACCESS, settings=settings)
    refresh_claims = decode_token(refresh, expected_type=TokenType.REFRESH, settings=settings)

    assert access_claims.tenant_id == tenant_id
    assert access_claims.user_id == user_id
    assert access_claims.role == "property_manager"
    assert access_claims.token_type == TokenType.ACCESS
    assert refresh_claims.token_type == TokenType.REFRESH


def test_decode_token_rejects_wrong_token_type() -> None:
    settings = _settings()
    access, _ = issue_token_pair(tenant_id=uuid4(), user_id=uuid4(), role="accountant", settings=settings)

    with pytest.raises(InvalidTokenError):
        decode_token(access, expected_type=TokenType.REFRESH, settings=settings)


def test_decode_token_rejects_bad_signature() -> None:
    access, _ = issue_token_pair(tenant_id=uuid4(), user_id=uuid4(), role="accountant", settings=_settings())

    with pytest.raises(InvalidTokenError):
        decode_token(
            access,
            settings=Settings(jwt_secret="a-completely-different-secret-value!!", jwt_issuer="crepro-test"),
        )


def test_decode_token_rejects_garbage() -> None:
    with pytest.raises(InvalidTokenError):
        decode_token("not-a-jwt", settings=_settings())
