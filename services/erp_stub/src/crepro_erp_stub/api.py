"""HTTP routes mimicking the subset of ERPNext's REST API that erp_client.py (the
real ERP client, services/erp_adapter/src/crepro_erp_adapter/erp_client.py) calls:
GET/POST/PATCH/DELETE /api/resource/{doctype}[/{name}], filtered list queries, and
a health check.

Not a real ERPNext -- a stand-in for Dev/smoke-test environments where standing up
the real external ERP (several containers: app, worker, scheduler, MariaDB, Redis)
is out of scope (see DAY14_PLAN.md).
"""

import json
import logging

from crepro_erp_stub.store import store
from fastapi import APIRouter, HTTPException, Request, Response, status

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_filters(filters_raw: str | None) -> list[list] | None:
    if not filters_raw:
        return None
    try:
        parsed = json.loads(filters_raw)
    except json.JSONDecodeError:
        logger.warning("Ignoring malformed filters: %r", filters_raw)
        return None
    return parsed if isinstance(parsed, list) else None


def _apply_filters(records: list[dict], filters: list[list]) -> list[dict]:
    for field, op, value in filters:
        if op == "=":
            records = [r for r in records if str(r.get(field)) == str(value)]
        elif op == ">=":
            records = [r for r in records if str(r.get(field, "")) >= str(value)]
        else:
            logger.warning("Unsupported filter operator: %s", op)
    return records


@router.get("/api/health", tags=["ops"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/resource/{doctype}", tags=["resource"])
def list_resource(doctype: str, request: Request) -> dict:
    """Covers erp_client.py's get_by_platform_id, get_all, and get_modified_since,
    which all GET this same endpoint with different filters/order_by/limit_page_length."""
    filters = _parse_filters(request.query_params.get("filters"))
    order_by = request.query_params.get("order_by", "")
    limit = int(request.query_params.get("limit_page_length", 0) or 0)

    records = store.list_all(doctype)
    if filters:
        records = _apply_filters(records, filters)
    if order_by.startswith("modified"):
        records = sorted(records, key=lambda r: r.get("modified", ""))
    if limit:
        records = records[:limit]

    return {"data": records}


@router.post("/api/resource/{doctype}", tags=["resource"])
async def create_resource(doctype: str, request: Request) -> dict:
    payload = await request.json()
    record = store.create(doctype, payload)
    logger.info("Created %s %s", doctype, record["name"])
    return {"data": record}


@router.get("/api/resource/{doctype}/{name}", tags=["resource"])
def get_resource(doctype: str, name: str) -> dict:
    record = store.get(doctype, name)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{doctype} {name} not found")
    return {"data": record}


@router.patch("/api/resource/{doctype}/{name}", tags=["resource"])
async def update_resource(doctype: str, name: str, request: Request) -> dict:
    updates = await request.json()
    record = store.update(doctype, name, updates)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{doctype} {name} not found")
    return {"data": record}


@router.delete("/api/resource/{doctype}/{name}", status_code=status.HTTP_202_ACCEPTED, tags=["resource"])
def delete_resource(doctype: str, name: str) -> Response:
    if not store.delete(doctype, name):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{doctype} {name} not found")
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post("/api/test/reset", tags=["test-only"])
def reset() -> dict[str, str]:
    """Clears all stored records. A smoke-test convenience; not part of the ERPNext API."""
    store.reset()
    return {"status": "reset"}
