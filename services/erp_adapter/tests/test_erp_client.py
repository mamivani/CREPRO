"""Direct unit tests for ERPClient: the real HTTP client for ERPNext, built in
Day 14 Phase 1 but (until push.py was wired to use it) never actually invoked
by the running service, and never itself unit-tested.
"""

from uuid import uuid4

import httpx
import pytest
import respx
from crepro_erp_adapter.erp_client import ERPClient

BASE_URL = "https://erp.example.com"


def _client() -> ERPClient:
    return ERPClient(base_url=BASE_URL, username="Administrator", password="secret")


def test_base_url_strips_trailing_slash() -> None:
    client = ERPClient(base_url="https://erp.example.com/", username="u", password="p")

    assert client.base_url == "https://erp.example.com"


@pytest.mark.asyncio
async def test_get_by_platform_id_returns_record_when_found() -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/api/resource/Customer").mock(
            return_value=httpx.Response(200, json={"data": [{"name": "CUST-001"}]})
        )
        record = await _client().get_by_platform_id("Customer", str(uuid4()))

    assert record == {"name": "CUST-001"}


@pytest.mark.asyncio
async def test_get_by_platform_id_returns_none_when_not_found() -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/api/resource/Customer").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        record = await _client().get_by_platform_id("Customer", str(uuid4()))

    assert record is None


@pytest.mark.asyncio
async def test_get_by_platform_id_raises_on_http_error() -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/api/resource/Customer").mock(return_value=httpx.Response(500))
        with pytest.raises(httpx.HTTPStatusError):
            await _client().get_by_platform_id("Customer", str(uuid4()))


@pytest.mark.asyncio
async def test_get_by_platform_id_raises_on_non_http_error() -> None:
    """A 2xx response with a malformed body hits the generic `except Exception` path."""
    with respx.mock:
        respx.get(f"{BASE_URL}/api/resource/Customer").mock(
            return_value=httpx.Response(200, content=b"not json")
        )
        with pytest.raises(ValueError):
            await _client().get_by_platform_id("Customer", str(uuid4()))


@pytest.mark.asyncio
async def test_create_posts_payload_and_returns_record() -> None:
    with respx.mock:
        route = respx.post(f"{BASE_URL}/api/resource/Customer").mock(
            return_value=httpx.Response(200, json={"data": {"name": "CUST-002"}})
        )
        record = await _client().create("Customer", {"customer_name": "Acme"})

    assert record == {"name": "CUST-002"}
    assert route.called


@pytest.mark.asyncio
async def test_create_raises_on_http_error() -> None:
    with respx.mock:
        respx.post(f"{BASE_URL}/api/resource/Customer").mock(return_value=httpx.Response(400))
        with pytest.raises(httpx.HTTPStatusError):
            await _client().create("Customer", {"customer_name": "Acme"})


@pytest.mark.asyncio
async def test_create_raises_on_non_http_error() -> None:
    with respx.mock:
        respx.post(f"{BASE_URL}/api/resource/Customer").mock(
            return_value=httpx.Response(200, content=b"not json")
        )
        with pytest.raises(ValueError):
            await _client().create("Customer", {"customer_name": "Acme"})


@pytest.mark.asyncio
async def test_update_patches_record() -> None:
    with respx.mock:
        respx.patch(f"{BASE_URL}/api/resource/Customer/CUST-001").mock(
            return_value=httpx.Response(200, json={"data": {"name": "CUST-001", "email_id": "a@b.com"}})
        )
        record = await _client().update("Customer", "CUST-001", {"email_id": "a@b.com"})

    assert record["email_id"] == "a@b.com"


@pytest.mark.asyncio
async def test_update_raises_on_http_error() -> None:
    with respx.mock:
        respx.patch(f"{BASE_URL}/api/resource/Customer/CUST-001").mock(return_value=httpx.Response(404))
        with pytest.raises(httpx.HTTPStatusError):
            await _client().update("Customer", "CUST-001", {})


@pytest.mark.asyncio
async def test_update_raises_on_non_http_error() -> None:
    with respx.mock:
        respx.patch(f"{BASE_URL}/api/resource/Customer/CUST-001").mock(
            return_value=httpx.Response(200, content=b"not json")
        )
        with pytest.raises(ValueError):
            await _client().update("Customer", "CUST-001", {})


@pytest.mark.asyncio
async def test_get_all_returns_data_list() -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/api/resource/Customer").mock(
            return_value=httpx.Response(200, json={"data": [{"name": "CUST-001"}, {"name": "CUST-002"}]})
        )
        records = await _client().get_all("Customer")

    assert len(records) == 2


@pytest.mark.asyncio
async def test_get_all_raises_on_http_error() -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/api/resource/Customer").mock(return_value=httpx.Response(500))
        with pytest.raises(httpx.HTTPStatusError):
            await _client().get_all("Customer")


@pytest.mark.asyncio
async def test_get_all_raises_on_non_http_error() -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/api/resource/Customer").mock(
            return_value=httpx.Response(200, content=b"not json")
        )
        with pytest.raises(ValueError):
            await _client().get_all("Customer")


@pytest.mark.asyncio
async def test_get_modified_since_returns_data_list() -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/api/resource/Customer").mock(
            return_value=httpx.Response(200, json={"data": [{"name": "CUST-001"}]})
        )
        records = await _client().get_modified_since("Customer", "2026-01-01T00:00:00")

    assert records == [{"name": "CUST-001"}]


@pytest.mark.asyncio
async def test_get_modified_since_raises_on_http_error() -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/api/resource/Customer").mock(return_value=httpx.Response(500))
        with pytest.raises(httpx.HTTPStatusError):
            await _client().get_modified_since("Customer", "2026-01-01T00:00:00")


@pytest.mark.asyncio
async def test_get_modified_since_raises_on_non_http_error() -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/api/resource/Customer").mock(
            return_value=httpx.Response(200, content=b"not json")
        )
        with pytest.raises(ValueError):
            await _client().get_modified_since("Customer", "2026-01-01T00:00:00")


def _paged_handler(total: int):
    """Fake Frappe list endpoint that honours limit_start and limit_page_length."""
    rows = [{"name": f"CUST-{i:04d}"} for i in range(total)]

    def handler(request: httpx.Request) -> httpx.Response:
        start = int(request.url.params.get("limit_start", 0))
        size = int(request.url.params.get("limit_page_length", 20))
        return httpx.Response(200, json={"data": rows[start : start + size]})

    return handler


@pytest.mark.asyncio
async def test_get_all_pages_past_the_page_size() -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/api/resource/Customer").mock(side_effect=_paged_handler(1234))
        records = await _client().get_all("Customer", limit=500)

    assert len(records) == 1234
    assert records[0] == {"name": "CUST-0000"}
    assert records[-1] == {"name": "CUST-1233"}


@pytest.mark.asyncio
async def test_get_modified_since_pages_past_the_page_size() -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/api/resource/Customer").mock(side_effect=_paged_handler(500))
        records = await _client().get_modified_since("Customer", "2026-01-01T00:00:00", limit=500)

    assert len(records) == 500


@pytest.mark.asyncio
async def test_get_all_returns_empty_list_when_no_records() -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/api/resource/Customer").mock(side_effect=_paged_handler(0))
        assert await _client().get_all("Customer") == []


@pytest.mark.asyncio
async def test_delete_succeeds() -> None:
    with respx.mock:
        route = respx.delete(f"{BASE_URL}/api/resource/Customer/CUST-001").mock(
            return_value=httpx.Response(202)
        )
        await _client().delete("Customer", "CUST-001")

    assert route.called


@pytest.mark.asyncio
async def test_delete_raises_on_http_error() -> None:
    with respx.mock:
        respx.delete(f"{BASE_URL}/api/resource/Customer/CUST-001").mock(return_value=httpx.Response(404))
        with pytest.raises(httpx.HTTPStatusError):
            await _client().delete("Customer", "CUST-001")


@pytest.mark.asyncio
async def test_delete_raises_on_non_http_error() -> None:
    with respx.mock:
        respx.delete(f"{BASE_URL}/api/resource/Customer/CUST-001").mock(side_effect=RuntimeError("boom"))
        with pytest.raises(RuntimeError):
            await _client().delete("Customer", "CUST-001")


@pytest.mark.asyncio
async def test_health_check_true_when_reachable() -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/api/health").mock(return_value=httpx.Response(200))
        assert await _client().health_check() is True


@pytest.mark.asyncio
async def test_health_check_false_on_error_status() -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/api/health").mock(return_value=httpx.Response(500))
        assert await _client().health_check() is False


@pytest.mark.asyncio
async def test_health_check_false_when_unreachable() -> None:
    with respx.mock:
        respx.get(f"{BASE_URL}/api/health").mock(side_effect=httpx.ConnectError("refused"))
        assert await _client().health_check() is False
