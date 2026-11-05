# Day 14 Plan: Full Pipeline Deployment & Smoke Tests

> **Correction (post-Phase 3):** Phase 3's Terraform (`infrastructure/terraform/`) deployed a
> second, ad-hoc Azure environment (`crepro-dev-rg`) instead of extending the project's actual
> baseline infra (`infra/terraform/environments/dev`, Day 3, resource group `rg-crepro-dev`,
> which already provisions a Container App Environment, Postgres, Service Bus, and Key Vault for
> exactly this purpose). That ad-hoc environment has been torn down. Any future Azure deployment
> work for Day 14 should add Container Apps/Jobs to `infra/terraform/environments/dev` instead of
> creating a parallel stack. Pipeline wiring gaps found while preparing that deployment (missing
> outbox relay, missing Dapr subscription, erp_adapter not using the real ERP client) are fixed
> independently of infra and do not require Azure.

## Overview
Deploy all 11 domain services + ERP adapter + reconciliation job to Azure Dev environment and run smoke tests to verify end-to-end ERP sync with exactly-once semantics.

**Exit Criteria:** All services running on Azure Container Apps, smoke tests passing, ERP sync verified end-to-end.

---

## Phase 1: Real Client Implementation (2 hours)

### 1.1 ERP Client Real Implementation
**Location:** `services/erp_adapter/src/crepro_erp_adapter/erp_client.py`

Replace mock with HTTP-based client:
```python
import requests
from requests.auth import HTTPBasicAuth

class ERPClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.auth = HTTPBasicAuth(username, password)
    
    def get_by_platform_id(self, doctype: str, platform_id: str):
        # GET /api/resource/{doctype}?filters=[["platform_id","=","{platform_id}"]]
        
    def create(self, doctype: str, payload: dict):
        # POST /api/resource/{doctype}
        
    def update(self, doctype: str, docid: str, payload: dict):
        # PATCH /api/resource/{doctype}/{docid}
```

**Configuration via Environment:**
- `ERP_BASE_URL` - https://erp.example.com
- `ERP_USERNAME` - API user
- `ERP_PASSWORD` - (from Azure Key Vault)

### 1.2 Ledger Repository Real Implementation
**Location:** `services/erp_adapter/src/crepro_erp_adapter/ledger_repo.py`

Replace mock with PostgreSQL:
```python
class PostgresLedgerRepo:
    def __init__(self, connection_string):
        self.pool = asyncpg.create_pool(connection_string)
    
    async def get_by_platform_id(self, tenant_id, platform_id):
        # SELECT * FROM ledger_entries WHERE tenant_id = ? AND platform_id = ?
        
    async def create(self, entry: LedgerEntry):
        # INSERT INTO ledger_entries (...)
        
    async def update(self, entry_id, updates: dict):
        # UPDATE ledger_entries SET ... WHERE id = ?
```

**Database Schema (already exists from Day 11):**
```sql
CREATE TABLE ledger_entries (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    platform_id UUID UNIQUE,
    entity_id UUID NOT NULL,
    entity_type VARCHAR(50),
    status VARCHAR(20),  -- POSTED, FAILED, DELETED, RECONCILED
    attempts INT DEFAULT 0,
    last_error TEXT,
    erp_docid VARCHAR(255),
    external_doctype VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 1.3 DLQ Repository Real Implementation
**Location:** `services/erp_adapter/src/crepro_erp_adapter/dlq_repo.py`

Replace mock with Dapr state management or PostgreSQL:
```python
class DaprDLQRepo:
    def __init__(self, dapr_client):
        self.dapr = dapr_client
    
    async def store_event(self, event: DLQEvent):
        # dapr.save_state("dlq-store", event_id, event)
        
    async def get_pending_events(self, tenant_id, hours=24):
        # dapr.query_state("dlq-store", query)
```

---

## Phase 2: Reconciliation Integration (1 hour)

### 2.1 Connect Reconciliation to Real Services
**Location:** `services/erp_reconciliation/src/crepro_erp_reconciliation/main.py`

Replace mock clients with real implementations:
```python
# Old (mock)
erp_client = MockERPClient()
ledger_repo = MockLedgerRepo()

# New (real)
erp_client = ERPClient(
    base_url=os.getenv("ERP_BASE_URL"),
    username=os.getenv("ERP_USERNAME"),
    password=get_secret("erp-password")
)
ledger_repo = PostgresLedgerRepo(os.getenv("DATABASE_URL"))
dlq_repo = DaprDLQRepo(get_dapr_client())
adapter_client = AdapterServiceClient(os.getenv("ADAPTER_SERVICE_URL"))
```

### 2.2 Add Real Dapr Integration
- Subscribe to `dead_letter_events` topic (from Day 12 DLQ routing)
- Call adapter service `/api/repost` endpoint with event payload
- Handle async responses (job runs on schedule, not triggered by pub/sub)

---

## Phase 3: Azure Deployment (3 hours)

### 3.1 Create Azure Resources
**Terraform files** in `infrastructure/terraform/`:

```hcl
# Container Apps Environment
resource "azurerm_container_app_environment" "crepro" {
  name                           = "crepro-dev"
  location                       = var.location
  resource_group_name            = azurerm_resource_group.crepro.name
  log_analytics_workspace_id     = azurerm_log_analytics_workspace.crepro.id
}

# Container Registry for images
resource "azurerm_container_registry" "crepro" {
  name                = "creprobuilddev"
  resource_group_name = azurerm_resource_group.crepro.name
  location            = var.location
  sku                 = "Standard"
  admin_enabled       = true
}

# Database
resource "azurerm_postgresql_server" "crepro" {
  name                = "crepro-db-dev"
  location            = var.location
  resource_group_name = azurerm_resource_group.crepro.name
  sku_name            = "B_Gen5_2"
  storage_mb          = 51200
}

# Azure Container Apps for each service
resource "azurerm_container_app" "property_service" {
  name              = "property-service"
  environment_id    = azurerm_container_app_environment.crepro.id
  resource_group_name = azurerm_resource_group.crepro.name
  # ... service config
}

# Container Apps Jobs for reconciliation
resource "azurerm_container_app_job" "erp_reconciliation_incremental" {
  name              = "erp-reconciliation-incremental"
  environment_id    = azurerm_container_app_environment.crepro.id
  
  cron_expression   = "*/15 * * * *"  # Every 15 minutes
  execution_type    = "Scheduled"
  
  template {
    container {
      name  = "reconciliation"
      image = "${azurerm_container_registry.crepro.login_server}/crepro-erp-reconciliation:latest"
      
      env {
        name  = "RECONCILIATION_MODE"
        value = "INCREMENTAL"
      }
    }
  }
}

resource "azurerm_container_app_job" "erp_reconciliation_full" {
  name              = "erp-reconciliation-full"
  environment_id    = azurerm_container_app_environment.crepro.id
  
  cron_expression   = "0 2 * * *"  # 2 AM every night
  execution_type    = "Scheduled"
  
  template {
    container {
      name  = "reconciliation"
      image = "${azurerm_container_registry.crepro.login_server}/crepro-erp-reconciliation:latest"
      
      env {
        name  = "RECONCILIATION_MODE"
        value = "FULL"
      }
    }
  }
}
```

### 3.2 Build & Push Container Images
```bash
# 1. Build all service images
for service in property tenant identity lease payment maintenance document utility reporting reservation erp_adapter erp_reconciliation; do
  cd services/$service
  docker build -t creprobuilddev.azurecr.io/crepro-$service:latest .
  docker push creprobuilddev.azurecr.io/crepro-$service:latest
  cd ../..
done

# 2. Deploy with Terraform
cd infrastructure/terraform
terraform init
terraform apply -var-file="dev.tfvars"
```

### 3.3 Configure Secrets in Azure Key Vault
```bash
az keyvault secret set --name erp-password --vault-name crepro-dev --value "<password>"
az keyvault secret set --name db-connection-string --vault-name crepro-dev --value "postgresql://..."
az keyvault secret set --name dapr-state-key --vault-name crepro-dev --value "<key>"
```

---

## Phase 4: Smoke Tests (2 hours)

### 4.1 Test Setup
**Location:** `tests/smoke/` (new directory)

```python
import asyncio
import httpx
from uuid import UUID, uuid4
from datetime import datetime

class SmokeTest:
    def __init__(self):
        self.property_service = "http://property-service.crepro-dev.svc.cluster.local"
        self.erp_service = "http://erp-adapter.crepro-dev.svc.cluster.local"
        self.tenant_id = UUID("00000000-0000-0000-0000-000000000001")  # Dev tenant
```

### 4.2 Smoke Test 1: Create Property & Verify in ERP
```python
async def test_create_property_syncs_to_erp():
    """
    Given: Empty ERP
    When: Create Property
    Then: Property appears in ERP with platform_id
    And: Ledger entry created with status POSTED
    """
    # 1. Create property in domain
    response = await property_service.post(
        "/api/properties",
        json={
            "name": "Test Property",
            "type": "RESIDENTIAL",
            "address": "123 Main St",
            "tenant_id": str(tenant_id)
        }
    )
    property_id = response.json()["id"]
    
    # 2. Wait for Dapr pub/sub delivery
    await asyncio.sleep(2)
    
    # 3. Verify in ERP
    erp_record = await erp_client.get_by_platform_id(
        "Property",
        property_id
    )
    assert erp_record is not None
    assert erp_record["platform_id"] == str(property_id)
    assert erp_record["status"] == "Active"
    
    # 4. Verify ledger entry
    ledger = await ledger_repo.get_by_platform_id(tenant_id, property_id)
    assert ledger.status == "POSTED"
    assert ledger.attempts == 1
```

### 4.3 Smoke Test 2: ERP Down During Posting
```python
async def test_retry_policy_on_erp_unavailable():
    """
    Given: ERP is down
    When: Create Customer
    Then: Adapter retries with exponential backoff [1, 2, 4, 8, 16] seconds
    And: After max retries, route to DLQ
    And: Ledger shows FAILED with error
    """
    # 1. Simulate ERP down
    erp_client.simulate_down()
    
    # 2. Create customer
    response = await domain_service.post(
        "/api/customers",
        json={"name": "Test Customer"}
    )
    customer_id = response.json()["id"]
    
    # 3. Wait for retries (max 31 seconds)
    await asyncio.sleep(35)
    
    # 4. Verify ledger shows FAILED
    ledger = await ledger_repo.get_by_platform_id(tenant_id, customer_id)
    assert ledger.status == "FAILED"
    assert ledger.attempts == 5  # Max retries
    assert "Connection refused" in ledger.last_error
    
    # 5. Verify event in DLQ
    dlq_events = await dlq_repo.get_pending_events(tenant_id)
    assert any(e.entity_id == customer_id for e in dlq_events)
```

### 4.4 Smoke Test 3: DLQ Recovery
```python
async def test_dlq_recovery_on_erp_restart():
    """
    Given: ERP was down, event in DLQ
    When: ERP comes back up
    And: Reconciliation job runs
    Then: DLQ replay attempts re-post
    And: Upon success, ledger status → POSTED
    And: DLQ event marked RECOVERED
    """
    # 1. Bring ERP back online
    erp_client.simulate_up()
    
    # 2. Trigger incremental reconciliation (or wait for 15-min schedule)
    response = await reconciliation_service.post(
        "/api/reconcile",
        json={"mode": "DLQ_REPLAY", "tenant_id": str(tenant_id)}
    )
    
    # 3. Wait for completion
    await asyncio.sleep(5)
    
    # 4. Verify ledger updated
    ledger = await ledger_repo.get_by_platform_id(tenant_id, customer_id)
    assert ledger.status == "POSTED"  # Now successful
    
    # 5. Verify DLQ event recovered
    dlq_event = await dlq_repo.get_event(customer_id)
    assert dlq_event.status == "RECOVERED"
```

### 4.5 Smoke Test 4: Idempotency Protection
```python
async def test_duplicate_event_creates_one_erp_record():
    """
    Given: Event published twice (Dapr at-least-once)
    When: Both reach ERP adapter
    Then: Only one ERP record created
    And: Both attempts update same ledger entry
    """
    # 1. Create invoice
    invoice = await domain_service.post(
        "/api/invoices",
        json={
            "customer_id": customer_id,
            "amount": 1000,
            "due_date": "2026-12-01"
        }
    )
    invoice_id = invoice.json()["id"]
    
    # 2. Simulate pub/sub publishing twice
    for _ in range(2):
        await dapr_pubsub.publish(
            topic="erp-events",
            message={
                "event_id": str(uuid4()),  # Unique event ID
                "entity_id": str(invoice_id),
                "action": "CREATE"
            }
        )
    
    # 3. Wait for both deliveries
    await asyncio.sleep(3)
    
    # 4. Verify single ERP record
    erp_records = await erp_client.query_by_platform_id("Invoice", invoice_id)
    assert len(erp_records) == 1  # Not 2
    
    # 5. Verify ledger attempts = 2
    ledger = await ledger_repo.get_by_platform_id(tenant_id, invoice_id)
    assert ledger.attempts == 2
```

### 4.6 Smoke Test 5: Full Reconciliation
```python
async def test_full_scan_detects_inconsistencies():
    """
    Given: 10 entities in ledger, 9 in ERP (1 deleted externally)
    When: Full reconciliation runs
    Then: Detects DELETED_IN_ERP discrepancy
    And: Marks for manual review
    """
    # 1. Create 10 entities
    for i in range(10):
        await domain_service.post("/api/properties", json={"name": f"Property {i}"})
    
    # 2. Simulate external deletion (remove one from ERP)
    erp_records = await erp_client.get_all("Property")
    await erp_client.delete(erp_records[0])  # Delete first one
    
    # 3. Wait for reconciliation
    response = await reconciliation_service.post(
        "/api/reconcile",
        json={"mode": "FULL", "tenant_id": str(tenant_id)}
    )
    
    # 4. Verify discrepancy detected
    discrepancies = await reconciliation_service.get(
        "/api/discrepancies",
        params={"type": "DELETED_IN_ERP", "tenant_id": str(tenant_id)}
    )
    assert len(discrepancies.json()) == 1
```

---

## Phase 5: Monitoring & Observability (1 hour)

### 5.1 Application Insights Setup
```hcl
resource "azurerm_application_insights" "crepro" {
  name                = "crepro-insights-dev"
  location            = var.location
  resource_group_name = azurerm_resource_group.crepro.name
  application_type    = "web"
}

resource "azurerm_monitor_diagnostic_setting" "container_app" {
  name                       = "crepro-logs"
  target_resource_id         = azurerm_container_app_environment.crepro.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.crepro.id
  
  log {
    category = "ContainerAppSystemLogs"
    enabled  = true
  }
}
```

### 5.2 Alerts
```python
# Create alert for:
# - ERP Adapter failures > 5% in last 5 min
# - DLQ queue size > 100
# - Reconciliation job failure
# - Database connection errors
```

---

## Exit Criteria Checklist

- [ ] ERP Client real implementation (HTTP-based)
- [ ] Ledger Repository real implementation (PostgreSQL)
- [ ] DLQ Repository real implementation (Dapr/PostgreSQL)
- [ ] Reconciliation main.py uses real clients
- [ ] All 11 domain services deployed to Azure
- [ ] ERP Adapter deployed to Azure
- [ ] Reconciliation job deployed (incremental + full)
- [ ] Smoke test 1: Create property syncs to ERP ✓
- [ ] Smoke test 2: Retry policy on ERP unavailable ✓
- [ ] Smoke test 3: DLQ recovery on ERP restart ✓
- [ ] Smoke test 4: Idempotency protection ✓
- [ ] Smoke test 5: Full reconciliation detects inconsistencies ✓
- [ ] Application Insights collecting logs
- [ ] Alerts configured and tested
- [ ] All services accessible from Azure
- [ ] No test regressions from Days 11-13

---

## Known Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| ERP API rate limiting | Implement request batching, cache API calls |
| Database connection pool exhaustion | Monitor pool usage, set appropriate limits |
| Reconciliation job timeout | Set reasonable timeout, split large batches |
| Dapr pub/sub message loss | Enable durability, verify delivery guarantees |
| Secret rotation | Implement Azure Key Vault automatic rotation |

---

## Time Budget
- Phase 1: 2 hours (real clients)
- Phase 2: 1 hour (reconciliation integration)
- Phase 3: 3 hours (Azure deployment)
- Phase 4: 2 hours (smoke tests)
- Phase 5: 1 hour (monitoring)
- **Total: 9 hours** (target: 1 full day)

---

## Success Metrics
- ✅ All 5 smoke tests passing
- ✅ Zero ERP sync failures in 1-hour test run
- ✅ Reconciliation job completes < 5 minutes (incremental), < 30 minutes (full)
- ✅ DLQ recovery success rate > 95%
- ✅ All services healthy in Azure Container Apps
