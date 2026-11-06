"""PostgreSQL-backed DLQ repository for dead-lettered ERP events.

The adapter writes failed posts here (push.route_to_dlq) and the reconciliation
job reads and updates them (dlq_replay). Both sides share the dlq_events table
in the platform database, so the job runs in Container Apps Jobs without a Dapr sidecar.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)

# Columns update() may set; identity and routing columns are never rewritten.
_UPDATABLE_COLUMNS = {"status", "retry_count", "last_retry_at"}


@dataclass
class DLQEventRecord:
    """Attribute-accessible DLQ row, matching the names dlq_replay.py reads."""

    id: UUID
    tenant_id: UUID
    original_event_id: UUID
    entity_id: UUID
    external_doctype: str
    reason: str
    original_payload: dict
    status: str
    retry_count: int
    routed_at: datetime
    last_retry_at: datetime | None = None

    @classmethod
    def from_row(cls, row: asyncpg.Record) -> "DLQEventRecord":
        data = dict(row)
        data["original_event_id"] = data.pop("event_id")
        data["entity_id"] = data.pop("platform_entity_id")
        data["original_payload"] = _as_dict(data.pop("payload"))
        return cls(**data)


def _as_dict(value: Any) -> dict:
    """asyncpg returns JSONB as text unless a codec is registered; accept both."""
    if isinstance(value, str):
        return json.loads(value)
    return dict(value or {})


class PostgresDLQRepo:
    """PostgreSQL repository for dead-lettered ERP events."""

    def __init__(self, connection_string: str, pool_size: int = 5):
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        self.pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=1,
            max_size=self.pool_size,
            command_timeout=60,
        )
        logger.info("PostgreSQL DLQ connection pool initialized")

    async def shutdown(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("PostgreSQL DLQ connection pool closed")

    async def store_event(
        self,
        event_id: UUID,
        tenant_id: UUID,
        entity_id: UUID,
        external_doctype: str,
        reason: str,
        payload: dict,
    ) -> None:
        """Insert a dead-lettered event. Redelivery of the same event_id is a no-op."""
        await self.pool.execute(
            """
            INSERT INTO dlq_events (
                tenant_id, event_id, platform_entity_id, external_doctype,
                reason, payload, status, retry_count, routed_at
            )
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, 'PENDING', 0, $7)
            ON CONFLICT (event_id) DO NOTHING
            """,
            tenant_id,
            event_id,
            entity_id,
            external_doctype,
            reason,
            json.dumps(payload),
            datetime.utcnow(),
        )

    async def get_pending_events(
        self,
        tenant_id: UUID,
        routed_after: datetime,
        status: str = "PENDING",
    ) -> list[DLQEventRecord]:
        """Return events with the given status routed at or after routed_after."""
        rows = await self.pool.fetch(
            """
            SELECT id, tenant_id, event_id, platform_entity_id, external_doctype,
                   reason, payload, status, retry_count, routed_at, last_retry_at
            FROM dlq_events
            WHERE tenant_id = $1 AND routed_at >= $2 AND status = $3
            ORDER BY routed_at
            """,
            tenant_id,
            routed_after,
            status,
        )
        return [DLQEventRecord.from_row(row) for row in rows]

    async def get_latest_for_entity(self, tenant_id: UUID, entity_id: UUID) -> DLQEventRecord | None:
        """Return the most recently routed DLQ event for an entity, if any."""
        row = await self.pool.fetchrow(
            """
            SELECT id, tenant_id, event_id, platform_entity_id, external_doctype,
                   reason, payload, status, retry_count, routed_at, last_retry_at
            FROM dlq_events
            WHERE tenant_id = $1 AND platform_entity_id = $2
            ORDER BY routed_at DESC
            LIMIT 1
            """,
            tenant_id,
            entity_id,
        )
        return DLQEventRecord.from_row(row) if row else None

    async def update(self, record_id: UUID, **updates: Any) -> None:
        """Update whitelisted columns on one DLQ row."""
        unknown = set(updates) - _UPDATABLE_COLUMNS
        if unknown:
            raise ValueError(f"Columns not updatable on dlq_events: {sorted(unknown)}")
        if not updates:
            return

        assignments = ", ".join(f"{col} = ${i}" for i, col in enumerate(updates, start=2))
        await self.pool.execute(
            f"UPDATE dlq_events SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = $1",
            record_id,
            *updates.values(),
        )
