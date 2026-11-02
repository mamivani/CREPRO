"""Direct unit tests for TenantDirectoryClient and resolve_tenant, independent of the
fakes used by test_auth.py's end-to-end login flows.
"""

from uuid import uuid4

import httpx
import pytest
from crepro_identity.tenant_resolution import TenantDirectoryClient, TenantResolutionError, resolve_tenant


def _client_for(handler) -> TenantDirectoryClient:
    transport = httpx.MockTransport(handler)
    return TenantDirectoryClient(client=httpx.Client(transport=transport, base_url="http://tenant.test"))


def test_directory_client_returns_tenant_id_on_match() -> None:
    tenant_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["host"] == "acme.crepro.app"
        return httpx.Response(200, json={"id": str(tenant_id)})

    directory = _client_for(handler)

    assert directory.resolve_by_host("acme.crepro.app") == tenant_id


def test_directory_client_returns_none_on_404() -> None:
    directory = _client_for(lambda request: httpx.Response(404))

    assert directory.resolve_by_host("no-such-tenant.example.com") is None


def test_directory_client_raises_on_server_error() -> None:
    directory = _client_for(lambda request: httpx.Response(500))

    with pytest.raises(httpx.HTTPStatusError):
        directory.resolve_by_host("acme.crepro.app")


class _StubDirectory:
    def __init__(self, result) -> None:
        self._result = result

    def resolve_by_host(self, host: str):
        return self._result


def test_resolve_tenant_prefers_host_match_over_claim() -> None:
    host_tenant, claimed_tenant = uuid4(), uuid4()

    resolved = resolve_tenant(
        host="acme.crepro.app", claimed_tenant_id=claimed_tenant, directory=_StubDirectory(host_tenant)
    )

    assert resolved == host_tenant


def test_resolve_tenant_falls_back_to_claim_when_host_unresolved() -> None:
    claimed_tenant = uuid4()

    resolved = resolve_tenant(
        host="unknown.example.com", claimed_tenant_id=claimed_tenant, directory=_StubDirectory(None)
    )

    assert resolved == claimed_tenant


def test_resolve_tenant_falls_back_to_claim_when_no_host() -> None:
    claimed_tenant = uuid4()

    resolved = resolve_tenant(host=None, claimed_tenant_id=claimed_tenant, directory=_StubDirectory(None))

    assert resolved == claimed_tenant


def test_resolve_tenant_raises_when_nothing_resolves() -> None:
    with pytest.raises(TenantResolutionError):
        resolve_tenant(host="unknown.example.com", claimed_tenant_id=None, directory=_StubDirectory(None))
