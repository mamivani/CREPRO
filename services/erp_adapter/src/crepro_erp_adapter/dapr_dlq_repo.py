"""Dapr-based DLQ repository for dead-lettered event recovery.

Uses Dapr state management to store dead-lettered events that failed posting.
Provides recovery interface for Day 13 reconciliation job.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class DaprDLQRepo:
    """Dapr-based repository for dead-lettered events."""

    def __init__(self, dapr_client: Any, state_store: str = "dlq-store"):
        """
        Initialize Dapr DLQ repository.

        Args:
            dapr_client: Dapr client instance (from dapr.clients)
            state_store: Dapr state store name
        """
        self.dapr_client = dapr_client
        self.state_store = state_store

    async def store_event(
        self,
        event_id: UUID,
        tenant_id: UUID,
        entity_id: UUID,
        external_doctype: str,
        reason: str,
        payload: dict,
    ) -> None:
        """
        Store a dead-lettered event.

        Args:
            event_id: Unique event ID
            tenant_id: Tenant UUID
            entity_id: Platform entity ID
            external_doctype: ERP document type
            reason: Reason for DLQ routing
            payload: Original entity payload
        """
        dlq_event = {
            "event_id": str(event_id),
            "tenant_id": str(tenant_id),
            "entity_id": str(entity_id),
            "external_doctype": external_doctype,
            "reason": reason,
            "payload": payload,
            "status": "PENDING",
            "retry_count": 0,
            "routed_at": datetime.utcnow().isoformat(),
            "last_retry_at": None,
        }

        try:
            # Use Dapr state management to store the event
            # Key format: dlq:{tenant_id}:{event_id}
            key = f"dlq:{tenant_id}:{event_id}"
            
            # Simulate storing via Dapr (real implementation uses dapr_client.save_state)
            # For testing, we'd mock this
            self.dapr_client.save_state(
                self.state_store,
                key,
                json.dumps(dlq_event),
            )
            logger.info(f"Stored DLQ event: {event_id}")

        except Exception as exc:
            logger.error(f"Error storing DLQ event: {exc}")
            raise

    async def get_pending_events(
        self,
        tenant_id: UUID,
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """
        Get pending DLQ events routed within the last N hours.

        Args:
            tenant_id: Tenant UUID
            hours: Hours to look back (default 24)

        Returns:
            List of pending DLQ events
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # Query Dapr state store for events matching this tenant
            # For testing, we'd implement this with a query pattern
            events = []

            # Simulate querying with pattern: dlq:{tenant_id}:*
            # Real implementation would use Dapr query API
            query_result = self.dapr_client.query_state(
                self.state_store,
                f"dlq:{tenant_id}:*",
            )

            if query_result and query_result.get("results"):
                for result in query_result["results"]:
                    event_data = json.loads(result.get("value", "{}"))

                    # Filter by routed_at timestamp
                    routed_at = datetime.fromisoformat(
                        event_data.get("routed_at", "")
                    )
                    if routed_at >= cutoff_time and event_data.get("status") == "PENDING":
                        events.append(event_data)

            logger.info(f"Found {len(events)} pending DLQ events for tenant {tenant_id}")
            return events

        except Exception as exc:
            logger.error(f"Error querying pending DLQ events: {exc}")
            raise

    async def update_event(
        self,
        event_id: UUID,
        tenant_id: UUID,
        updates: dict,
    ) -> None:
        """
        Update a DLQ event.

        Args:
            event_id: Event ID
            tenant_id: Tenant UUID
            updates: Dict with fields to update (status, retry_count, last_retry_at)
        """
        try:
            key = f"dlq:{tenant_id}:{event_id}"

            # Fetch current event
            current_json = self.dapr_client.get_state(self.state_store, key)
            if not current_json:
                logger.warning(f"DLQ event not found: {event_id}")
                return

            event = json.loads(current_json.data)

            # Update fields
            if "status" in updates:
                event["status"] = updates["status"]
            if "retry_count" in updates:
                event["retry_count"] = updates["retry_count"]
            if "last_retry_at" in updates:
                event["last_retry_at"] = updates["last_retry_at"]

            # Save updated event
            self.dapr_client.save_state(
                self.state_store,
                key,
                json.dumps(event),
            )
            logger.info(f"Updated DLQ event: {event_id} -> {updates}")

        except Exception as exc:
            logger.error(f"Error updating DLQ event: {exc}")
            raise

    async def mark_recovered(self, event_id: UUID, tenant_id: UUID) -> None:
        """Mark a DLQ event as successfully recovered."""
        await self.update_event(
            event_id,
            tenant_id,
            {"status": "RECOVERED", "last_retry_at": datetime.utcnow().isoformat()},
        )

    async def mark_manual_review(self, event_id: UUID, tenant_id: UUID) -> None:
        """Mark a DLQ event for manual review after max retries."""
        await self.update_event(
            event_id,
            tenant_id,
            {"status": "MANUAL_REVIEW_REQUIRED"},
        )

    async def increment_retry_count(self, event_id: UUID, tenant_id: UUID) -> int:
        """Increment retry count for an event and return new count."""
        try:
            key = f"dlq:{tenant_id}:{event_id}"
            current_json = self.dapr_client.get_state(self.state_store, key)

            if not current_json:
                logger.warning(f"DLQ event not found: {event_id}")
                return 0

            event = json.loads(current_json.data)
            new_count = event.get("retry_count", 0) + 1
            event["retry_count"] = new_count
            event["last_retry_at"] = datetime.utcnow().isoformat()

            self.dapr_client.save_state(
                self.state_store,
                key,
                json.dumps(event),
            )

            return new_count

        except Exception as exc:
            logger.error(f"Error incrementing retry count: {exc}")
            raise

    async def delete_event(self, event_id: UUID, tenant_id: UUID) -> None:
        """Delete a resolved DLQ event."""
        try:
            key = f"dlq:{tenant_id}:{event_id}"
            self.dapr_client.delete_state(self.state_store, key)
            logger.info(f"Deleted DLQ event: {event_id}")
        except Exception as exc:
            logger.error(f"Error deleting DLQ event: {exc}")
            raise


class DaprDLQRepoSync:
    """Synchronous wrapper for Dapr DLQ repository."""

    def __init__(self, dapr_client: Any, state_store: str = "dlq-store"):
        """Initialize sync DLQ repository wrapper."""
        import asyncio

        self.dapr_client = dapr_client
        self.state_store = state_store
        self.repo = DaprDLQRepo(dapr_client, state_store)
        self.loop = asyncio.new_event_loop()

    def store_event(
        self,
        event_id: UUID,
        tenant_id: UUID,
        entity_id: UUID,
        external_doctype: str,
        reason: str,
        payload: dict,
    ) -> None:
        """Sync wrapper for store_event."""
        self.loop.run_until_complete(
            self.repo.store_event(
                event_id, tenant_id, entity_id, external_doctype, reason, payload
            )
        )

    def get_pending_events(self, tenant_id: UUID, hours: int = 24) -> list[dict]:
        """Sync wrapper for get_pending_events."""
        return self.loop.run_until_complete(
            self.repo.get_pending_events(tenant_id, hours)
        )

    def update_event(self, event_id: UUID, tenant_id: UUID, updates: dict) -> None:
        """Sync wrapper for update_event."""
        self.loop.run_until_complete(
            self.repo.update_event(event_id, tenant_id, updates)
        )

    def mark_recovered(self, event_id: UUID, tenant_id: UUID) -> None:
        """Sync wrapper for mark_recovered."""
        self.loop.run_until_complete(self.repo.mark_recovered(event_id, tenant_id))

    def mark_manual_review(self, event_id: UUID, tenant_id: UUID) -> None:
        """Sync wrapper for mark_manual_review."""
        self.loop.run_until_complete(self.repo.mark_manual_review(event_id, tenant_id))

    def increment_retry_count(self, event_id: UUID, tenant_id: UUID) -> int:
        """Sync wrapper for increment_retry_count."""
        return self.loop.run_until_complete(
            self.repo.increment_retry_count(event_id, tenant_id)
        )

    def delete_event(self, event_id: UUID, tenant_id: UUID) -> None:
        """Sync wrapper for delete_event."""
        self.loop.run_until_complete(self.repo.delete_event(event_id, tenant_id))
