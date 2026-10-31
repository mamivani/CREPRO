from uuid import uuid4

import pytest
from crepro_common import EventEnvelope, TenantContext, TenantNotSetError, create_app, current_tenant
from crepro_common.tenancy import bind_tenant, unbind_tenant


def test_create_app_exposes_health() -> None:
    from fastapi.testclient import TestClient

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
