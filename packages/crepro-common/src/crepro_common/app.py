import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from crepro_common.models import OutboxEntry
from crepro_common.outbox_relay import run_outbox_relay_forever
from crepro_common.repository import InMemoryRepository
from crepro_common.telemetry import instrument_app


def create_app(
    service_name: str,
    *,
    outbox: InMemoryRepository[OutboxEntry] | None = None,
    outbox_topic: str = "erp-events",
) -> FastAPI:
    """Build the shared FastAPI app scaffold.

    When `outbox` is given, also runs a background task for the lifetime of
    the app that relays that service's PENDING outbox entries to Dapr
    pub/sub on `outbox_topic` (crepro_common.outbox_relay). Services without
    an outbox (or whose entries are emitted by another process) omit it and
    get the scaffold with no background task, exactly as before.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        relay_task = (
            asyncio.create_task(run_outbox_relay_forever(outbox, topic=outbox_topic))
            if outbox is not None
            else None
        )
        try:
            yield
        finally:
            if relay_task is not None:
                relay_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await relay_task

    app = FastAPI(title=f"CREPRO {service_name}", version="0.1.0", lifespan=lifespan)

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"service": service_name, "status": "ok"}

    instrument_app(app, service_name)
    return app
