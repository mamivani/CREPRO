"""ERP Reconciliation Job - Main entry point.

Supports both real and mock clients for development/testing/production.
Configuration via environment variables:
- RECONCILIATION_MODE: INCREMENTAL or FULL
- TENANT_ID: UUID of tenant to reconcile
- ERP_BASE_URL: Optional ERP base URL (if set, uses real ERP client)
- DATABASE_URL: Optional PostgreSQL connection string
- DAPR_STATE_STORE: Optional Dapr state store name
"""

import asyncio
import logging
import os
from datetime import datetime
from uuid import UUID

from .incremental_scan import run_incremental_scan
from .full_scan import run_full_scan
from .dlq_replay import replay_dlq_events

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class MockERPClient:
    """Mock ERP client for development/testing."""

    async def query_modified_records(self, tenant_id, modified_after, doctypes):
        """Query ERP for records modified since a time."""
        return []

    async def query_all_records(self, tenant_id, doctypes):
        """Query all ERP records."""
        return []

    async def get_record(self, tenant_id, doctype, docid):
        """Get a specific ERP record."""
        return None


class MockLedgerRepo:
    """Mock ledger repository for development/testing."""

    def get_last_incremental_scan(self, tenant_id):
        """Get last incremental scan time."""
        return None

    def update_last_incremental_scan(self, tenant_id, timestamp):
        """Update last incremental scan time."""
        pass

    def update_last_full_scan(self, tenant_id, timestamp):
        """Update last full scan time."""
        pass

    def get_by_platform_id(self, tenant_id, platform_id):
        """Get ledger entry by platform ID."""
        return None

    def create(self, **kwargs):
        """Create a ledger entry."""
        pass

    def get_all(self, tenant_id, statuses):
        """Get all ledger entries for a tenant with given statuses."""
        return []

    def update(self, entry_id, **kwargs):
        """Update a ledger entry."""
        pass


class MockDLQRepo:
    """Mock DLQ repository for development/testing."""

    def get_pending_events(self, tenant_id, routed_after, status):
        """Get pending DLQ events."""
        return []

    def update(self, event_id, **kwargs):
        """Update a DLQ event."""
        pass


class MockAdapterClient:
    """Mock adapter service client."""

    async def post_to_erp_with_retry(self, tenant_id, entity_id, external_doctype, payload, dlq_replay=False):
        """Post to ERP with retry."""
        return False, None


async def _initialize_clients():
    """
    Initialize ERP clients based on environment.

    If production URLs provided, uses real clients. Otherwise uses mocks for testing.
    
    Returns:
        (erp_client, ledger_repo, dlq_repo, adapter_client) tuple
    """
    # Check if we should use real clients
    erp_base_url = os.getenv("ERP_BASE_URL")
    database_url = os.getenv("DATABASE_URL")
    adapter_service_url = os.getenv("ADAPTER_SERVICE_URL")

    if erp_base_url and database_url and adapter_service_url:
        logger.info("Initializing production clients")
        
        # Import real clients (lazy import to avoid dependency if not needed)
        from crepro_erp_adapter.erp_client import ERPClient
        from crepro_erp_adapter.postgres_ledger_repo import PostgresLedgerRepo
        from crepro_erp_adapter.dapr_dlq_repo import DaprDLQRepo
        from crepro_erp_adapter.adapter_service_client import AdapterServiceClient

        # Get credentials from environment/Key Vault
        erp_username = os.getenv("ERP_USERNAME", "Administrator")
        erp_password = os.getenv("ERP_PASSWORD", "")  # Should come from Key Vault

        # Initialize real ERP client
        erp_client = ERPClient(
            base_url=erp_base_url,
            username=erp_username,
            password=erp_password,
        )

        # Initialize real ledger repository
        ledger_repo = PostgresLedgerRepo(database_url)
        await ledger_repo.initialize()

        # Initialize real DLQ repository (requires Dapr client)
        try:
            from dapr.clients import DaprClient
            dapr_client = DaprClient()
            dlq_repo = DaprDLQRepo(dapr_client)
        except Exception:
            logger.warning("Dapr client not available, falling back to mock DLQ repo", exc_info=True)
            dlq_repo = MockDLQRepo()

        # Initialize adapter service client
        adapter_client = AdapterServiceClient(adapter_service_url)

        logger.info("Production clients initialized successfully")
        return erp_client, ledger_repo, dlq_repo, adapter_client

    else:
        logger.info("Using mock clients (development/testing mode)")
        return MockERPClient(), MockLedgerRepo(), MockDLQRepo(), MockAdapterClient()


async def run_reconciliation_job():
    """
    Main job entry point.

    Runs incremental scan, full scan, and DLQ replay based on environment.
    """
    mode = os.getenv("RECONCILIATION_MODE", "INCREMENTAL").upper()
    tenant_id_str = os.getenv("TENANT_ID", "00000000-0000-0000-0000-000000000000")
    
    try:
        tenant_id = UUID(tenant_id_str)
    except ValueError:
        logger.error(f"Invalid TENANT_ID: {tenant_id_str}")
        return

    # Initialize clients based on environment
    erp_client, ledger_repo, dlq_repo, adapter_client = await _initialize_clients()

    logger.info(f"Starting reconciliation job in {mode} mode for tenant {tenant_id}")

    try:
        if mode == "INCREMENTAL":
            # Run incremental scan (every 15 minutes)
            logger.info("Running incremental scan...")
            report = await run_incremental_scan(
                tenant_id=tenant_id,
                erp_client=erp_client,
                ledger_repo=ledger_repo,
                dlq_repo=dlq_repo,
            )
            logger.info(f"Incremental scan report: {report}")

            # Also run DLQ replay
            logger.info("Running DLQ replay...")
            dlq_report = await replay_dlq_events(
                tenant_id=tenant_id,
                dlq_repo=dlq_repo,
                adapter_client=adapter_client,
            )
            logger.info(f"DLQ replay report: {dlq_report}")

        elif mode == "FULL":
            # Run full scan (nightly)
            logger.info("Running full scan...")
            report = await run_full_scan(
                tenant_id=tenant_id,
                erp_client=erp_client,
                ledger_repo=ledger_repo,
            )
            logger.info(f"Full scan report: {report}")

        else:
            logger.error(f"Unknown reconciliation mode: {mode}")

        logger.info("Reconciliation job completed successfully")

    except Exception as e:
        logger.error(f"Reconciliation job failed: {e}", exc_info=True)
        raise
    finally:
        # Cleanup
        if hasattr(ledger_repo, 'shutdown'):
            await ledger_repo.shutdown()



def main():
    """CLI entry point."""
    asyncio.run(run_reconciliation_job())


if __name__ == "__main__":  # pragma: no cover -- exercised by running the module, not by import
    main()
