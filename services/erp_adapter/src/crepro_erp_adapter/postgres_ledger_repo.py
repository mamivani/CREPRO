"""PostgreSQL-based ledger repository for ERP adapter.

Stores audit trail of all ERP sync operations with retry tracking, and the
per-tenant reconciliation_state row (last incremental/full scan times) Day 13's
incremental_scan/full_scan modules read and update on every run.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)

# Columns update() is allowed to set via **updates; always-sensitive columns
# (id, tenant_id, platform_entity_id, created_at) are deliberately excluded.
_UPDATABLE_COLUMNS = {
    "status",
    "attempts",
    "last_error",
    "erp_docid",
    "event_type",
    "external_doctype",
    "notes",
}


@dataclass
class LedgerEntryRecord:
    """Attribute-accessible ledger row, matching the interface
    incremental_scan.py/full_scan.py (and tests/conftest.py's MockLedgerRepo)
    already expect -- e.g. `entry.status`, `entry.entity_id`, not dict keys.
    """

    id: UUID
    tenant_id: UUID
    entity_id: UUID
    status: str
    external_doctype: str
    event_type: str | None = None
    payload_hash: str | None = None
    attempts: int = 0
    last_error: str | None = None
    erp_docid: str | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_row(cls, row: asyncpg.Record) -> "LedgerEntryRecord":
        data = dict(row)
        data["entity_id"] = data.pop("platform_entity_id")
        return cls(**data)


class PostgresLedgerRepo:
    """PostgreSQL ledger repository for adapter audit trail."""

    def __init__(self, connection_string: str, pool_size: int = 10):
        """
        Initialize PostgreSQL ledger repository.

        Args:
            connection_string: PostgreSQL connection URL
            pool_size: Connection pool size
        """
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.pool = None

    async def initialize(self) -> None:
        """Initialize connection pool."""
        self.pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=2,
            max_size=self.pool_size,
            command_timeout=60,
        )
        logger.info("PostgreSQL connection pool initialized")

    async def shutdown(self) -> None:
        """Shutdown connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")

    async def get_by_platform_id(
        self,
        tenant_id: UUID,
        platform_id: UUID,
    ) -> LedgerEntryRecord | None:
        """
        Get ledger entry by platform ID.

        Args:
            tenant_id: Tenant UUID
            platform_id: Platform entity ID

        Returns:
            LedgerEntryRecord or None
        """
        query = """
            SELECT id, tenant_id, platform_entity_id, event_type, external_doctype,
                   payload_hash, status, attempts, last_error, erp_docid, notes,
                   created_at, updated_at
            FROM adapter_ledger_entries
            WHERE tenant_id = $1 AND platform_entity_id = $2
            LIMIT 1
        """
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, tenant_id, platform_id)
                return LedgerEntryRecord.from_row(row) if row else None
        except Exception as exc:
            logger.error(f"Error querying ledger by platform_id: {exc}")
            raise

    async def create(
        self,
        tenant_id: UUID,
        entity_id: UUID,
        status: str,
        erp_docid: str | None = None,
        external_doctype: str | None = None,
        attempts: int = 0,
        notes: str | None = None,
        event_type: str | None = None,
        payload_hash: str | None = None,
        last_error: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> LedgerEntryRecord:
        """
        Create a new ledger entry.

        `event_type`/`payload_hash` are only set when posting an original domain
        event (push.py's flow); entries incremental_scan/full_scan create or infer
        from observed ERP state have neither.
        """
        query = """
            INSERT INTO adapter_ledger_entries (
                tenant_id, platform_entity_id, event_type, external_doctype,
                payload_hash, status, attempts, last_error, erp_docid, notes,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id, tenant_id, platform_entity_id, event_type, external_doctype,
                      payload_hash, status, attempts, last_error, erp_docid, notes,
                      created_at, updated_at
        """
        try:
            now = datetime.utcnow()
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    tenant_id,
                    entity_id,
                    event_type,
                    external_doctype,
                    payload_hash,
                    status,
                    attempts,
                    last_error,
                    erp_docid,
                    notes,
                    created_at or now,
                    updated_at or now,
                )
                logger.info(f"Created ledger entry: {entity_id}")
                return LedgerEntryRecord.from_row(row)
        except Exception as exc:
            logger.error(f"Error creating ledger entry: {exc}")
            raise

    async def update(self, entry_id: UUID, **updates: Any) -> LedgerEntryRecord | None:
        """
        Update a ledger entry.

        Args:
            entry_id: Ledger entry ID
            **updates: Fields to update (see _UPDATABLE_COLUMNS); `updated_at` is
                always set, to the caller's value if given, else now().

        Returns:
            Updated LedgerEntryRecord, or None if entry_id doesn't exist.
        """
        set_clauses = []
        values: list[Any] = [entry_id]
        param_count = 2

        for key, value in updates.items():
            if key in _UPDATABLE_COLUMNS:
                set_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1

        set_clauses.append(f"updated_at = ${param_count}")
        values.append(updates.get("updated_at") or datetime.utcnow())

        query = f"""
            UPDATE adapter_ledger_entries
            SET {", ".join(set_clauses)}
            WHERE id = $1
            RETURNING id, tenant_id, platform_entity_id, event_type, external_doctype,
                      payload_hash, status, attempts, last_error, erp_docid, notes,
                      created_at, updated_at
        """

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, *values)
                if row:
                    logger.info(f"Updated ledger entry: {entry_id}")
                    return LedgerEntryRecord.from_row(row)
                return None
        except Exception as exc:
            logger.error(f"Error updating ledger entry: {exc}")
            raise

    async def get_all(
        self,
        tenant_id: UUID,
        statuses: list[str] | None = None,
        limit: int = 1000,
    ) -> list[LedgerEntryRecord]:
        """
        Get all ledger entries for a tenant with optional status filter.

        Args:
            tenant_id: Tenant UUID
            statuses: Optional list of statuses to filter by
            limit: Max records to return

        Returns:
            List of LedgerEntryRecord
        """
        if statuses:
            status_placeholders = ", ".join(f"${i}" for i in range(2, len(statuses) + 2))
            query = f"""
                SELECT id, tenant_id, platform_entity_id, event_type, external_doctype,
                       payload_hash, status, attempts, last_error, erp_docid, notes,
                       created_at, updated_at
                FROM adapter_ledger_entries
                WHERE tenant_id = $1 AND status IN ({status_placeholders})
                ORDER BY created_at DESC
                LIMIT {limit}
            """
            values = [tenant_id] + statuses
        else:
            query = f"""
                SELECT id, tenant_id, platform_entity_id, event_type, external_doctype,
                       payload_hash, status, attempts, last_error, erp_docid, notes,
                       created_at, updated_at
                FROM adapter_ledger_entries
                WHERE tenant_id = $1
                ORDER BY created_at DESC
                LIMIT {limit}
            """
            values = [tenant_id]

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *values)
                return [LedgerEntryRecord.from_row(row) for row in rows]
        except Exception as exc:
            logger.error(f"Error querying all ledger entries: {exc}")
            raise

    async def count_by_status(self, tenant_id: UUID) -> dict[str, int]:
        """
        Count ledger entries by status.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dict mapping status to count
        """
        query = """
            SELECT status, COUNT(*) as count
            FROM adapter_ledger_entries
            WHERE tenant_id = $1
            GROUP BY status
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, tenant_id)
                return {row["status"]: row["count"] for row in rows}
        except Exception as exc:
            logger.error(f"Error counting ledger entries by status: {exc}")
            raise

    # --- Reconciliation scan tracking (Day 13: incremental_scan/full_scan) ---
    # Backed by reconciliation_state, one row per tenant, upserted on each call.

    async def get_last_incremental_scan(self, tenant_id: UUID) -> datetime | None:
        return await self._get_scan_timestamp(tenant_id, "last_incremental_scan")

    async def get_last_full_scan(self, tenant_id: UUID) -> datetime | None:
        return await self._get_scan_timestamp(tenant_id, "last_full_scan")

    async def update_last_incremental_scan(self, tenant_id: UUID, timestamp: datetime) -> None:
        await self._upsert_scan_timestamp(tenant_id, "last_incremental_scan", timestamp)

    async def update_last_full_scan(self, tenant_id: UUID, timestamp: datetime) -> None:
        await self._upsert_scan_timestamp(tenant_id, "last_full_scan", timestamp)

    async def _get_scan_timestamp(self, tenant_id: UUID, column: str) -> datetime | None:
        query = f"SELECT {column} FROM reconciliation_state WHERE tenant_id = $1"  # noqa: S608 (column is one of our own two literals, never caller input)
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetchval(query, tenant_id)
        except Exception as exc:
            logger.error(f"Error reading {column} for tenant {tenant_id}: {exc}")
            raise

    async def _upsert_scan_timestamp(self, tenant_id: UUID, column: str, timestamp: datetime) -> None:
        query = f"""
            INSERT INTO reconciliation_state (tenant_id, {column}, updated_at)
            VALUES ($1, $2, CURRENT_TIMESTAMP)
            ON CONFLICT (tenant_id) DO UPDATE
                SET {column} = EXCLUDED.{column}, updated_at = CURRENT_TIMESTAMP
        """  # noqa: S608 (column is one of our own two literals, never caller input)
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, tenant_id, timestamp)
        except Exception as exc:
            logger.error(f"Error updating {column} for tenant {tenant_id}: {exc}")
            raise
