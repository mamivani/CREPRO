# Day 14 Deployment Guide

## Overview

Day 14 implements full pipeline deployment to Azure Container Apps with real client implementations and smoke tests.

**Timeline:** 9 hours
**Status:** Phase 1 (Real Clients) Complete, Phases 2-5 Ready for Execution

---

## Phase 1: Real Client Implementation ✅

### 1.1 Created Real Clients

**ERP Client** (`services/erp_adapter/src/crepro_erp_adapter/erp_client.py`)
- HTTP-based with HTTPBasicAuth
- Methods: `get_by_platform_id()`, `create()`, `update()`, `get_all()`, `get_modified_since()`, `delete()`, `health_check()`
- Uses `httpx` for async HTTP requests
- Credentials from environment: `ERP_BASE_URL`, `ERP_USERNAME`, `ERP_PASSWORD`

**PostgreSQL Ledger Repository** (`services/erp_adapter/src/crepro_erp_adapter/postgres_ledger_repo.py`)
- Connection pooling with asyncpg
- Schema: `adapter_ledger_entries` table with full audit trail
- Tracks: status, attempts, last_error, erp_docid, timestamps
- Indexes on tenant_id, platform_entity_id, status for performance

**Dapr DLQ Repository** (`services/erp_adapter/src/crepro_erp_adapter/dapr_dlq_repo.py`)
- State management via Dapr
- Key format: `dlq:{tenant_id}:{event_id}`
- Methods: `store_event()`, `get_pending_events()`, `update_event()`, `mark_recovered()`, `mark_manual_review()`
- 24-hour retention window with retry tracking

**Adapter Service Client** (`services/erp_adapter/src/crepro_erp_adapter/adapter_service_client.py`)
- HTTP client for DLQ replay
- Endpoint: `POST /api/repost`
- Used by Day 13 reconciliation for recovery attempts

### 1.2 Updated Reconciliation Main

File: `services/erp_reconciliation/src/crepro_erp_reconciliation/main.py`

Added `_initialize_clients()` function that:
- Checks environment variables for production URLs
- If present: uses real clients (ERP, PostgreSQL, Dapr, Adapter)
- If absent: falls back to mock clients for testing
- Supports development/testing with mocks, production with real implementations

Environment Variables:
- `ERP_BASE_URL` - Triggers real ERP client
- `DATABASE_URL` - Triggers PostgreSQL ledger repo
- `ADAPTER_SERVICE_URL` - Adapter service endpoint
- `RECONCILIATION_MODE` - INCREMENTAL or FULL
- `TENANT_ID` - Tenant UUID to process

### 1.3 Database Schema

File: `infrastructure/database/01-adapter-ledger-schema.sql`

Tables created:
- `adapter_ledger_entries` - Audit trail (status, attempts, errors)
- `dlq_events` - Dead-lettered events (routed_at, retry_count, status)
- `reconciliation_state` - Tracking (last scan times, pending count)
- `reconciliation_discrepancies` - Detailed discrepancies (type, detected_at, resolved)

Indexes on:
- tenant_id, platform_entity_id, status
- created_at, updated_at for time-based queries
- Unique constraint on (tenant_id, platform_entity_id)

### 1.4 Test Status

✅ All 17 Day 13 tests still passing
✅ Real client code integrated without breaking tests
✅ Mock infrastructure remains for testing

---

## Phase 2: Reconciliation Integration

### 2.1 Environment Configuration

```bash
# Production environment variables for Container Apps
export ERP_BASE_URL="https://erp.example.com"
export ERP_USERNAME="Administrator"
export ERP_PASSWORD="$(az keyvault secret show --name erp-password --vault-name crepro-dev-kv --query value -o tsv)"
export DATABASE_URL="$(az keyvault secret show --name database-url --vault-name crepro-dev-kv --query value -o tsv)"
export ADAPTER_SERVICE_URL="http://erp-adapter.svc.cluster.local"
export DAPR_STATE_STORE="dlq-store"
```

### 2.2 Dapr Configuration

Container App Environment includes Dapr components:
- `pubsub` (Azure Service Bus) - erp-events and dead_letter_events topics
- `dlq-store` (Blob Storage) - State for DLQ events

Pub/sub scopes:
- erp-adapter: subscribes to erp-events, publishes to dead_letter_events
- erp-reconciliation: consumes dead_letter_events for replay

---

## Phase 3: Azure Deployment

### 3.1 Infrastructure Setup

**Terraform** (`infrastructure/terraform/main.tf`)

Resources created:
- Resource Group: crepro-dev-rg
- Container Registry: creprobuilddev
- PostgreSQL Server: crepro-db-dev (14, B2s SKU, 32 GB)
- Container App Environment: crepro-dev-env
- Log Analytics Workspace
- Application Insights
- Key Vault: crepro-dev-kv (for secrets)

### 3.2 Deployment Steps

```bash
# 1. Set up Azure CLI
az login
az account set --subscription YOUR-SUBSCRIPTION-ID

# 2. Update Terraform variables
cd infrastructure/terraform
# Edit dev.tfvars with your subscription ID

# 3. Initialize Terraform
terraform init

# 4. Set sensitive variables
export TF_VAR_erp_password="YOUR-ERP-PASSWORD"
export TF_VAR_postgres_password="YOUR-POSTGRES-PASSWORD"

# 5. Deploy infrastructure
terraform plan -var-file="dev.tfvars" -out=tfplan
terraform apply tfplan

# 6. Initialize database
psql -h $(terraform output -raw database_host) -U pgadmin -d crepro < infrastructure/database/01-adapter-ledger-schema.sql

# 7. Build and push container images
cd services/erp_adapter
docker build -t creprobuilddev.azurecr.io/crepro-erp-adapter:latest .
az acr login --name creprobuilddev
docker push creprobuilddev.azurecr.io/crepro-erp-adapter:latest

cd ../erp_reconciliation
docker build -t creprobuilddev.azurecr.io/crepro-erp-reconciliation:latest .
docker push creprobuilddev.azurecr.io/crepro-erp-reconciliation:latest

# 8. Deploy services (requires additional Container App Terraform config - Phase 3.3)
```

### 3.3 Container App Definitions

For each service, create Container App with:
- Image from registry
- Environment variables from Key Vault
- Dapr sidecar enabled
- Health checks
- Resource limits (CPU, memory)

Example for erp-adapter:
```yaml
apiVersion: containerapp.io/v1beta1
kind: ContainerApp
metadata:
  name: erp-adapter
spec:
  environmentId: /subscriptions/.../containerAppEnvironments/crepro-dev-env
  template:
    containers:
      - image: creprobuilddev.azurecr.io/crepro-erp-adapter:latest
        name: adapter
        env:
          - name: ERP_BASE_URL
            value: "https://erp.example.com"
          - name: DATABASE_URL
            secretRef: database-url
          - name: ERP_PASSWORD
            secretRef: erp-password
        resources:
          cpu: 1
          memory: 2Gi
    daprConfig:
      enabled: true
      appId: erp-adapter
      appPort: 8000
```

---

## Phase 4: Smoke Tests

### 4.1 Test 1: Create Property & Verify in ERP

```python
async def test_create_property_syncs_to_erp():
    # 1. Create property via domain service API
    # 2. Wait for pub/sub delivery (2 seconds)
    # 3. Query ERP by platform_id
    # 4. Verify platform_id set correctly
    # 5. Verify ledger entry status = POSTED
```

**Expected:** Property appears in ERP within 5 seconds

### 4.2 Test 2: Retry Policy on ERP Unavailable

```python
async def test_retry_policy_on_erp_unavailable():
    # 1. Simulate ERP down
    # 2. Create customer via domain service
    # 3. Wait 35 seconds (max retry time: 1+2+4+8+16 seconds)
    # 4. Verify ledger status = FAILED
    # 5. Verify attempts = 5
    # 6. Verify error in last_error field
```

**Expected:** Ledger shows max retries (5) exhausted

### 4.3 Test 3: DLQ Recovery on ERP Restart

```python
async def test_dlq_recovery_on_erp_restart():
    # 1. ERP comes back online
    # 2. Trigger incremental reconciliation (or wait 15 min)
    # 3. Verify DLQ replay attempts repost
    # 4. Verify ledger status updated to POSTED
    # 5. Verify DLQ event status = RECOVERED
```

**Expected:** Event recovered and appears in ERP

### 4.4 Test 4: Idempotency Protection

```python
async def test_duplicate_event_creates_one_erp_record():
    # 1. Publish same event twice (simulating Dapr at-least-once)
    # 2. Wait for both deliveries
    # 3. Query ERP - count records with platform_id
    # 4. Verify only 1 record (not 2)
    # 5. Verify ledger attempts = 2
```

**Expected:** Only 1 ERP record created despite 2 events

### 4.5 Test 5: Full Reconciliation

```python
async def test_full_scan_detects_inconsistencies():
    # 1. Create 10 entities
    # 2. Simulate external deletion in ERP (remove 1)
    # 3. Trigger full scan reconciliation
    # 4. Query discrepancies
    # 5. Verify DELETED_IN_ERP discrepancy found
```

**Expected:** Discrepancy detected and marked for review

---

## Phase 5: Monitoring & Observability

### 5.1 Application Insights Setup

Metrics to track:
- ERP Adapter:
  - Posted events (success rate)
  - Retry attempts distribution
  - DLQ routing rate
  - Latency p50/p95/p99

- Reconciliation:
  - Scan duration (incremental, full)
  - Discrepancies found (by type)
  - Recovery success rate
  - Manual review count

### 5.2 Alert Rules

```
# Critical Alerts
- ERP Adapter failure rate > 5% (5 min window)
- DLQ queue size > 100 events
- Reconciliation job timeout > 30 min (full scan)
- Database connection errors > 0
- Application Insights availability < 95%

# Warning Alerts
- ERP Adapter latency p95 > 5 seconds
- Reconciliation job failure
- Manual review items > 10
- Pending DLQ events > 50
```

### 5.3 Dashboards

Create Azure dashboards showing:
- ERP sync success/failure rate
- Ledger entry status distribution
- DLQ event timeline
- Reconciliation job execution times
- Error trends

---

## Deployment Checklist

### Pre-Deployment
- [ ] Verify all Day 13 tests passing
- [ ] Review Terraform configuration
- [ ] Prepare ERP credentials
- [ ] Set up Azure subscription

### Deployment
- [ ] Initialize Terraform
- [ ] Deploy Azure infrastructure
- [ ] Create PostgreSQL database
- [ ] Store secrets in Key Vault
- [ ] Build container images
- [ ] Push to registry
- [ ] Deploy Container Apps

### Post-Deployment
- [ ] Verify all services healthy
- [ ] Test health endpoints
- [ ] Run 5 smoke tests
- [ ] Verify monitoring/alerts working
- [ ] Document any issues

### Validation
- [ ] All services responding to /health
- [ ] Logs appearing in Application Insights
- [ ] Smoke tests 1-5 all passing
- [ ] No sync failures in 1-hour test run
- [ ] Reconciliation jobs completing < SLA

---

## Rollback Plan

If deployment fails:
```bash
# 1. Stop Container Apps (pause billing)
az containerapp stop -n erp-adapter -g crepro-dev-rg
az containerapp stop -n erp-reconciliation -g crepro-dev-rg

# 2. Destroy infrastructure
terraform destroy -var-file="dev.tfvars"

# 3. Address issues (check error logs in Application Insights)

# 4. Redeploy after fixes
```

---

## Next Steps After Day 14

### Day 15 (Documentation & Backlog)
- Generate code coverage reports
- Create comprehensive ops documentation
- Define Days 16-25 backlog (frontend development)
- Performance testing with 10k+ records

### Days 16-25 (Frontend Development)
- Responsive website (React + Tailwind)
- iOS mobile app (React Native)
- Android mobile app (React Native)
- End-to-end testing with Playwright

---

## Files Created/Modified in Day 14

### New Files
- `services/erp_adapter/src/crepro_erp_adapter/erp_client.py` (9.8 KB)
- `services/erp_adapter/src/crepro_erp_adapter/postgres_ledger_repo.py` (10.5 KB)
- `services/erp_adapter/src/crepro_erp_adapter/dapr_dlq_repo.py` (9.8 KB)
- `services/erp_adapter/src/crepro_erp_adapter/adapter_service_client.py` (4.2 KB)
- `infrastructure/database/01-adapter-ledger-schema.sql` (4.1 KB)
- `infrastructure/terraform/main.tf` (4.5 KB)
- `infrastructure/terraform/dev.tfvars` (0.5 KB)

### Modified Files
- `services/erp_reconciliation/src/crepro_erp_reconciliation/main.py` (Added client initialization)

### Test Status
- ✅ 17/17 Day 13 tests passing
- ✅ All real client code integrated
- ✅ Ready for Phase 3 deployment

---

## Contact & Support

For deployment issues:
1. Check Application Insights logs
2. Review error messages in Container App logs
3. Verify environment variables and secrets in Key Vault
4. Consult Terraform state file for resource status
