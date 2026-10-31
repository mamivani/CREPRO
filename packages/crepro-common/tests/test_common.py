from uuid import uuid4

import pytest
from crepro_common import (
    EntityNotFoundError,
    EventEnvelope,
    InMemoryRepository,
    TenantContext,
    TenantNotSetError,
    TenantScopedEntity,
    build_crud_router,
    create_app,
    current_tenant,
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
