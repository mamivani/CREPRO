"""Real HTTP-based ERP client for ERPNext integration.

Implements HTTP Basic Authentication as per ERPNext v15.124.3 REST API.
Uses Azure Key Vault for credential management.
"""

import logging
from typing import Any, Optional
from uuid import UUID

import httpx
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class ERPClient:
    """HTTP client for ERPNext/CommonERP integration."""

    def __init__(self, base_url: str, username: str, password: str, timeout: int = 30):
        """
        Initialize ERP client with credentials.

        Args:
            base_url: ERP server base URL (e.g., https://erp.example.com)
            username: API user username
            password: API user password
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = None

    def _get_headers(self) -> dict:
        """Get request headers with HTTP Basic Auth."""
        import base64
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def get_by_platform_id(
        self,
        doctype: str,
        platform_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Query ERP for a single record by platform_id custom field.

        Args:
            doctype: Document type (e.g., "Customer", "Invoice")
            platform_id: Platform entity ID to search for

        Returns:
            ERP record dict if found, None otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Query by custom_platform_id field (created during deployment)
                filters = f'[["custom_platform_id","=","{platform_id}"]]'
                url = f"{self.base_url}/api/resource/{doctype}"
                response = await client.get(
                    url,
                    params={"filters": filters, "fields": '["*"]'},
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                data = response.json()

                if data.get("data") and len(data["data"]) > 0:
                    return data["data"][0]
                return None

        except httpx.HTTPError as exc:
            logger.error(f"HTTP error querying {doctype} by platform_id: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Error querying {doctype} by platform_id: {exc}")
            raise

    async def create(self, doctype: str, payload: dict) -> dict[str, Any]:
        """
        Create a new record in ERP.

        Args:
            doctype: Document type (e.g., "Customer")
            payload: Record data with platform_id included

        Returns:
            Created record dict with name field

        Raises:
            httpx.HTTPError: On HTTP errors
            Exception: On other errors
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}/api/resource/{doctype}"
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                data = response.json()

                record = data.get("data", {})
                logger.info(
                    f"Created {doctype}: platform_id={payload.get('custom_platform_id')}, "
                    f"name={record.get('name')}"
                )
                return record

        except httpx.HTTPError as exc:
            logger.error(f"HTTP error creating {doctype}: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Error creating {doctype}: {exc}")
            raise

    async def update(
        self,
        doctype: str,
        docid: str,
        payload: dict,
    ) -> dict[str, Any]:
        """
        Update an existing record in ERP.

        Args:
            doctype: Document type
            docid: Document ID/name
            payload: Fields to update

        Returns:
            Updated record dict

        Raises:
            httpx.HTTPError: On HTTP errors
            Exception: On other errors
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}/api/resource/{doctype}/{docid}"
                response = await client.patch(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                data = response.json()

                record = data.get("data", {})
                logger.info(f"Updated {doctype}: {docid}")
                return record

        except httpx.HTTPError as exc:
            logger.error(f"HTTP error updating {doctype} {docid}: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Error updating {doctype} {docid}: {exc}")
            raise

    async def get_all(self, doctype: str, limit: int = 500) -> list[dict[str, Any]]:
        """
        Get all records of a document type.

        Args:
            doctype: Document type
            limit: Max records to fetch

        Returns:
            List of record dicts

        Raises:
            httpx.HTTPError: On HTTP errors
            Exception: On other errors
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}/api/resource/{doctype}"
                response = await client.get(
                    url,
                    params={"limit_page_length": limit},
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])

        except httpx.HTTPError as exc:
            logger.error(f"HTTP error fetching all {doctype}: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Error fetching all {doctype}: {exc}")
            raise

    async def get_modified_since(
        self,
        doctype: str,
        since: str,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """
        Get records modified since a timestamp.

        Args:
            doctype: Document type
            since: ISO format timestamp (e.g., "2026-11-03T15:00:00")
            limit: Max records to fetch

        Returns:
            List of modified record dicts

        Raises:
            httpx.HTTPError: On HTTP errors
            Exception: On other errors
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}/api/resource/{doctype}"
                # Query by modified timestamp
                filters = f'[["modified",">=","{since}"]]'
                response = await client.get(
                    url,
                    params={
                        "filters": filters,
                        "limit_page_length": limit,
                        "order_by": "modified asc",
                    },
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])

        except httpx.HTTPError as exc:
            logger.error(f"HTTP error fetching modified {doctype}: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Error fetching modified {doctype}: {exc}")
            raise

    async def delete(self, doctype: str, docid: str) -> None:
        """
        Delete a record from ERP.

        Args:
            doctype: Document type
            docid: Document ID/name

        Raises:
            httpx.HTTPError: On HTTP errors
            Exception: On other errors
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}/api/resource/{doctype}/{docid}"
                response = await client.delete(
                    url,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                logger.info(f"Deleted {doctype}: {docid}")

        except httpx.HTTPError as exc:
            logger.error(f"HTTP error deleting {doctype} {docid}: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Error deleting {doctype} {docid}: {exc}")
            raise

    async def health_check(self) -> bool:
        """
        Check ERP connectivity.

        Returns:
            True if ERP is reachable, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                url = f"{self.base_url}/api/health"
                response = await client.get(url, headers=self._get_headers())
                return response.status_code < 400
        except Exception as exc:
            logger.error(f"Health check failed: {exc}")
            return False
