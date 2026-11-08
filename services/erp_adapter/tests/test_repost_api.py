"""Tests for POST /api/repost, the reconciliation DLQ replay endpoint."""

from uuid import uuid4

import pytest
from crepro_erp_adapter import api
from crepro_erp_adapter.main import app
from fastapi.testclient import TestClient


def _body() -> dict:
    return {
        "tenant_id": str(uuid4()),
        "entity_id": str(uuid4()),
        "external_doctype": "Customer",
        "payload": {"name": "Acme"},
    }


@pytest.fixture(autouse=True)
def passthrough_mapping(monkeypatch):
    monkeypatch.setattr(api, "apply_entity_mapping", lambda doctype, payload: payload)


def test_repost_returns_existing_name_without_reposting(monkeypatch) -> None:
    async def already_posted(entity_id, doctype):
        return True, "CUST-001"

    async def must_not_post(*args, **kwargs):
        raise AssertionError("ERP post must not run for an already-posted entity")

    monkeypatch.setattr(api, "check_idempotency_internal", already_posted)
    monkeypatch.setattr(api, "post_to_erp_internal", must_not_post)

    response = TestClient(app).post("/api/repost", json=_body())

    assert response.status_code == 200
    assert response.json() == {"external_name": "CUST-001"}


def test_repost_posts_when_not_yet_in_erp(monkeypatch) -> None:
    async def not_posted(entity_id, doctype):
        return False, None

    async def post_ok(entity_id, doctype, payload):
        assert payload == {"name": "Acme"}
        return True, "CUST-002"

    monkeypatch.setattr(api, "check_idempotency_internal", not_posted)
    monkeypatch.setattr(api, "post_to_erp_internal", post_ok)

    response = TestClient(app).post("/api/repost", json=_body())

    assert response.status_code == 200
    assert response.json() == {"external_name": "CUST-002"}


def test_repost_returns_502_when_erp_post_fails(monkeypatch) -> None:
    async def not_posted(entity_id, doctype):
        return False, None

    async def post_fails(entity_id, doctype, payload):
        return False, None

    monkeypatch.setattr(api, "check_idempotency_internal", not_posted)
    monkeypatch.setattr(api, "post_to_erp_internal", post_fails)

    response = TestClient(app).post("/api/repost", json=_body())

    assert response.status_code == 502
