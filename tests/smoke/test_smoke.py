"""Day 14 smoke tests against a deployed dev environment.

Skipped unless SMOKE_SERVICE_URLS is set. Provide the Terraform output, e.g.:

    cd infra/terraform/environments/dev
    $env:SMOKE_SERVICE_URLS = (terraform output -json service_urls)

Each value is the Container App ingress FQDN; the tests call https://<fqdn>.
"""

import json
import os
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

SERVICE_URLS_JSON = os.environ.get("SMOKE_SERVICE_URLS", "")
SERVICE_FQDNS: dict[str, str] = json.loads(SERVICE_URLS_JSON) if SERVICE_URLS_JSON else {}

pytestmark = pytest.mark.skipif(
    not SERVICE_FQDNS, reason="SMOKE_SERVICE_URLS not set; smoke tests need a deployed environment"
)

TIMEOUT = 15


def _base(name: str) -> str:
    return f"https://{SERVICE_FQDNS[name]}"


@pytest.mark.parametrize("service", sorted(SERVICE_FQDNS))
def test_service_health(service: str) -> None:
    response = httpx.get(f"{_base(service)}/health", timeout=TIMEOUT)
    assert response.status_code == 200, response.text


def test_erp_events_delivery_is_idempotent() -> None:
    """Delivering the same erp-events envelope twice must not fail the second time.

    process_event checks platform_id before posting to ERP, so a redelivery (Dapr at-least-once)
    should be acknowledged with HTTP 200 both times.
    """
    if "erp_adapter" not in SERVICE_FQDNS:
        pytest.skip("erp_adapter is not deployed")

    envelope = {
        "event_id": str(uuid4()),
        "event_type": "property.created",
        "tenant_id": os.environ.get("SMOKE_TENANT_ID", str(uuid4())),
        "source": "smoke-test",
        "schema_version": "1",
        "occurred_at": datetime.now(UTC).isoformat(),
        "payload": {"id": str(uuid4()), "name": "Smoke Test Property"},
    }

    url = f"{_base('erp_adapter')}/subscribe/erp-events"
    first = httpx.post(url, json=envelope, timeout=TIMEOUT)
    second = httpx.post(url, json=envelope, timeout=TIMEOUT)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text


def test_dapr_subscription_is_registered() -> None:
    if "erp_adapter" not in SERVICE_FQDNS:
        pytest.skip("erp_adapter is not deployed")

    response = httpx.get(f"{_base('erp_adapter')}/dapr/subscribe", timeout=TIMEOUT)
    assert response.status_code == 200
    routes = [item["route"] for item in response.json()]
    assert "/subscribe/erp-events" in routes
