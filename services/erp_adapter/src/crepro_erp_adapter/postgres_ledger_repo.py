"""PostgreSQL-based ledger repository for ERP adapter.

Stores audit trail of all ERP sync operations with retry tracking.
Enables post-mortem analysis and reconciliation.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


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
    ) -> dict[str, Any] | None:
        """
        Get ledger entry by platform ID.

        Args:
            tenant_id: Tenant UUID
            platform_id: Platform entity ID

        Returns:
            Ledger entry dict or None
        """
        query = """
            SELECT id, tenant_id, platform_entity_id, event_type, external_doctype,
                   payload_hash, status, attempts, last_error, erp_docid, created_at, updated_at
            FROM adapter_ledger_entries
            WHERE tenant_id = $1 AND platform_entity_id = $2
            LIMIT 1
        """
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    tenant_id,
                    platform_id,
                )
                if row:
                    return dict(row)
                return None
        except Exception as exc:
            logger.error(f"Error querying ledger by platform_id: {exc}")
            raise

    async def create(self, entry: dict) -> dict[str, Any]:
        """
        Create a new ledger entry.

        Args:
            entry: Ledger entry dict with fields:
                - tenant_id (UUID)
                - platform_entity_id (UUID)
                - event_type (str)
                - external_doctype (str)
                - payload_hash (str)
                - status (str)
                - attempts (int)
                - last_error (str, optional)
                - erp_docid (str, optional)

        Returns:
            Created entry dict
        """
        query = """
            INSERT INTO adapter_ledger_entries (
                tenant_id, platform_entity_id, event_type, external_doctype,
                payload_hash, status, attempts, last_error, erp_docid,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id, tenant_id, platform_entity_id, event_type, external_doctype,
                      payload_hash, status, attempts, last_error, erp_docid,
                      created_at, updated_at
        """
        try:
            now = datetime.utcnow()
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    entry["tenant_id"],
                    entry["platform_entity_id"],
                    entry["event_type"],
                    entry["external_doctype"],
                    entry["payload_hash"],
                    entry["status"],
                    entry.get("attempts", 0),
                    entry.get("last_error"),
                    entry.get("erp_docid"),
                    now,
                    now,
                )
                logger.info(f"Created ledger entry: {entry['platform_entity_id']}")
                return dict(row)
        except Exception as exc:
            logger.error(f"Error creating ledger entry: {exc}")
            raise

    async def update(self, entry_id: UUID, updates: dict) -> dict[str, Any]:
        """
        Update a ledger entry.

        Args:
            entry_id: Ledger entry ID
            updates: Fields to update dict

        Returns:
            Updated entry dict
        """
        # Build dynamic UPDATE clause
        set_clauses = []
        values = [entry_id]
        param_count = 2

        for key, value in updates.items():
            if key in [
                "status",
                "attempts",
                "last_error",
                "erp_docid",
                "event_type",
            ]:
                set_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1

        # Always update updated_at
        set_clauses.append(f"updated_at = ${param_count}")
        values.append(datetime.utcnow())
        param_count += 1

        if not set_clauses:
            logger.warning(f"No valid fields to update for entry {entry_id}")
            return {}

        query = f"""
            UPDATE adapter_ledger_entries
            SET {", ".join(set_clauses)}
            WHERE id = $1
            RETURNING id, tenant_id, platform_entity_id, event_type, external_doctype,
                      payload_hash, status, attempts, last_error, erp_docid,
                      created_at, updated_at
        """

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, *values)
                if row:
                    logger.info(f"Updated ledger entry: {entry_id}")
                    return dict(row)
                return {}
        except Exception as exc:
            logger.error(f"Error updating ledger entry: {exc}")
            raise

    async def get_all(
        self,
        tenant_id: UUID,
        statuses: list[str] | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Get all ledger entries for a tenant with optional status filter.

        Args:
            tenant_id: Tenant UUID
            statuses: Optional list of statuses to filter by
            limit: Max records to return

        Returns:
            List of ledger entry dicts
        """
        if statuses:
            status_placeholders = ", ".join(f"${i}" for i in range(2, len(statuses) + 2))
            query = f"""
                SELECT id, tenant_id, platform_entity_id, event_type, external_doctype,
                       payload_hash, status, attempts, last_error, erp_docid,
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
                       payload_hash, status, attempts, last_error, erp_docid,
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
                return [dict(row) for row in rows]
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


class PostgresLedgerRepoSync:
    """Synchronous wrapper for PostgreSQL ledger repository (for sync code)."""

    def __init__(self, connection_string: str):
        """Initialize sync ledger repository wrapper."""
        import asyncio

        self.connection_string = connection_string
        self.loop = asyncio.new_event_loop()
        self.repo = PostgresLedgerRepo(connection_string)
        self.loop.run_until_complete(self.repo.initialize())

    def get_by_platform_id(self, tenant_id: UUID, platform_id: UUID) -> dict | None:
        """Sync wrapper for get_by_platform_id."""
        return self.loop.run_until_complete(self.repo.get_by_platform_id(tenant_id, platform_id))

    def create(self, entry: dict) -> dict:
        """Sync wrapper for create."""
        return self.loop.run_until_complete(self.repo.create(entry))

    def update(self, entry_id: UUID, updates: dict) -> dict:
        """Sync wrapper for update."""
        return self.loop.run_until_complete(self.repo.update(entry_id, updates))

    def get_all(self, tenant_id: UUID, statuses: list | None = None) -> list:
        """Sync wrapper for get_all."""
        return self.loop.run_until_complete(self.repo.get_all(tenant_id, statuses))

    def shutdown(self) -> None:
        """Shutdown connection pool."""
        self.loop.run_until_complete(self.repo.shutdown())
        self.loop.close()
