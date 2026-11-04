"""Client for calling ERP Adapter service for reposting events.

Day 13 reconciliation uses this to attempt recovery of dead-lettered events.
"""

import logging
from typing import Any, Optional
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)


class AdapterServiceClient:
    """HTTP client for calling ERP Adapter service."""

    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize adapter service client.

        Args:
            base_url: Adapter service base URL (e.g., http://erp-adapter.svc.cluster.local)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    async def repost_entity(
        self,
        tenant_id: UUID,
        entity_id: UUID,
        external_doctype: str,
        payload: dict,
    ) -> tuple[bool, Optional[str]]:
        """
        Attempt to repost an entity that previously failed.

        Used by Day 13 reconciliation DLQ replay for recovery.

        Args:
            tenant_id: Tenant UUID
            entity_id: Platform entity ID
            external_doctype: ERP document type
            payload: Entity payload to post

        Returns:
            (success, external_name) tuple where external_name is the ERP document ID/name
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/repost",
                    json={
                        "tenant_id": str(tenant_id),
                        "entity_id": str(entity_id),
                        "external_doctype": external_doctype,
                        "payload": payload,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    external_name = data.get("external_name")
                    logger.info(f"Reposted {external_doctype} {entity_id} -> {external_name}")
                    return True, external_name
                else:
                    logger.warning(
                        f"Repost failed for {external_doctype} {entity_id}: "
                        f"status={response.status_code}"
                    )
                    return False, None

        except httpx.TimeoutException:
            logger.error(f"Repost timeout for {external_doctype} {entity_id}")
            return False, None
        except Exception as exc:
            logger.error(f"Error reposting {external_doctype} {entity_id}: {exc}")
            return False, None

    async def health_check(self) -> bool:
        """
        Check adapter service connectivity.

        Returns:
            True if service is reachable, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code < 400
        except Exception as exc:
            logger.error(f"Adapter health check failed: {exc}")
            return False


class AdapterServiceClientSync:
    """Synchronous wrapper for adapter service client."""

    def __init__(self, base_url: str, timeout: int = 30):
        """Initialize sync adapter client wrapper."""
        import asyncio

        self.base_url = base_url
        self.timeout = timeout
        self.client = AdapterServiceClient(base_url, timeout)
        self.loop = asyncio.new_event_loop()

    def repost_entity(
        self,
        tenant_id: UUID,
        entity_id: UUID,
        external_doctype: str,
        payload: dict,
    ) -> tuple[bool, Optional[str]]:
        """Sync wrapper for repost_entity."""
        return self.loop.run_until_complete(
            self.client.repost_entity(tenant_id, entity_id, external_doctype, payload)
        )

    def health_check(self) -> bool:
        """Sync wrapper for health_check."""
        return self.loop.run_until_complete(self.client.health_check())
