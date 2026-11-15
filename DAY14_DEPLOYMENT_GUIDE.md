# Day 14 Deployment Guide

> **Correction:** the ad-hoc `crepro-dev-rg` environment this guide's Phase 3 describes has been
> torn down -- it duplicated the project's real baseline infra (`infra/terraform/environments/dev`,
> resource group `rg-crepro-dev`). Future deployment work should extend that Terraform instead of
> re-running Phase 3 as written here.
>
> **Update:** steps 5-7 of section 3.2 (build/push images, `terraform apply -var deploy_services=true`,
> smoke tests) now run automatically in [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)
> on every push to `main` (i.e. after a PR merges) -- including `apps/web`, the frontend, deployed as
> `ca-crepro-web`. The manual steps below are still accurate for a one-off/local deploy (e.g. from a
> laptop with `az login`), but routine deployment no longer needs them run by hand.

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

**Postgres DLQ Repository** (`services/erp_adapter/src/crepro_erp_adapter/postgres_dlq_repo.py`)
- Stores DLQ events in the platform `dlq_events` table, so the reconciliation jobs (no Dapr sidecar) can replay them
- Methods: `store_event()` (idempotent on `event_id`), `get_pending_events()`, `update()` (status, retry_count, last_retry_at)
- Replay attempts are capped at 2 (`MAX_REPLAY_ATTEMPTS`), then the row moves to `MANUAL_REVIEW_REQUIRED`

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
```

### 2.2 Dapr Configuration

Container App Environment includes Dapr components:
- `pubsub` (Azure Service Bus) - erp-events and dead_letter_events topics

DLQ events are stored in the platform PostgreSQL `dlq_events` table (not Dapr state), so the
reconciliation jobs, which have no Dapr sidecar, can read and replay them.

Pub/sub scopes:
- erp-adapter: subscribes to erp-events, publishes to dead_letter_events
- erp-reconciliation: consumes dead_letter_events for replay

---

## Phase 3: Azure Deployment

### 3.1 Infrastructure Setup

**Terraform** (`infra/terraform/environments/dev`, the only Azure stack; see the correction note above)

Foundation (always applied): resource group `rg-crepro-dev`, VNet with delegated subnets, private
PostgreSQL Flexible Server 16, Key Vault, storage account, Container Registry, Log Analytics,
Container App Environment, Service Bus namespace with the `erp-events` topic.

Day 14 additions (`apps.tf`, `observability.tf`), gated by `deploy_services` (default `false`):
- User-assigned identity with AcrPull on ACR and Key Vault Secrets User on the vault
- Dapr components on the environment: `pubsub` (`pubsub.azure.servicebus.topics`, scoped to
  `property` and `erp-adapter`)
- 11 service Container Apps (`ca-crepro-<service>`), Dapr app IDs, `/health` probes, secrets from Key Vault.
  `erp_adapter` is internal-only (its `/api/repost` is unauthenticated and writes to the ERP)
- Two Container Apps Jobs running `crepro_erp_reconciliation`: INCREMENTAL every 15 min, FULL daily at 02:00 UTC
- Application Insights (workspace-based) with its connection string in Key Vault, and a failed-requests
  alert when `alert_email` is set

### 3.2 Deployment Steps

```bash
# 1. Set up Azure CLI
az login
az account set --subscription YOUR-SUBSCRIPTION-ID

# 2. Initialize Terraform (state backend from backend.hcl)
cd infra/terraform/environments/dev
terraform init -backend-config=backend.hcl

# 3. Apply the foundation first (no images needed yet)
export TF_VAR_erp_password="YOUR-ERP-PASSWORD"   # stored in Key Vault as erp-password
terraform apply

# 4. Initialize database schema (Postgres is private: run from inside the VNet or via a jump host)
psql "host=$(terraform output -raw postgres_fqdn) user=creproadmin dbname=crepro sslmode=require" -f infrastructure/database/01-adapter-ledger-schema.sql

# 5. Build and push the images (names: crepro-<service>; build context is the repo root)
ACR=$(terraform output -raw container_registry_login_server)
az acr login --name "${ACR%%.*}"
for svc in identity tenant property lease reservation payment document utility maintenance reporting erp_adapter erp_reconciliation; do
  name=${svc//_/-}
  docker build -f "services/$svc/Dockerfile" -t "$ACR/crepro-$name:$IMAGE_TAG" .
  docker push "$ACR/crepro-$name:$IMAGE_TAG"
done

# 6. Deploy services, jobs and Dapr components
export TF_VAR_dev_tenant_id="TENANT-UUID"
export TF_VAR_erp_base_url="https://erp.example.com"
terraform apply -var deploy_services=true -var image_tag="$IMAGE_TAG" -var alert_email="you@example.com"

# 7. Smoke tests
export SMOKE_SERVICE_URLS="$(terraform output -json service_urls)"
python -m pytest tests/smoke -v
```

Known gaps for this phase:
- DLQ replay runs in the reconciliation jobs. The jobs have no Dapr sidecar, so DLQ events live in the
  platform PostgreSQL `dlq_events` table, which the adapter writes and the jobs read via `DATABASE_URL`.
  Replay re-posts through the adapter's `POST /api/repost`, with at most 2 attempts before `MANUAL_REVIEW_REQUIRED`.
  The `dlq_events` schema change in `infrastructure/database/01-adapter-ledger-schema.sql` must be applied to the
  private database before this works.
- Event subscription uses one mechanism everywhere: the adapter's `GET /dapr/subscribe`. The declarative `dapr/components/subscriptions.yaml` was removed, so local compose and Azure register the same route once.


### 3.3 Container App Definitions

Defined in `infra/terraform/environments/dev/apps.tf` (`azurerm_container_app.service`, one per service in `local.services`).
Each app has: a user-assigned identity, secrets referenced from Key Vault (`database-url`, `erp-password`,
`appinsights-connection-string`), a Dapr sidecar (`app_id` = service name with dashes), `/health` liveness and
readiness probes, and 0.25 vCPU / 0.5 GiB with 1–2 replicas. The `erp_adapter` app also gets `ERP_BASE_URL`,
`ERP_USERNAME`, `ERP_PASSWORD` and `CREPRO_DATABASE_URL` (DLQ writes go to Postgres).

`azurerm_container_app.erp_stub` runs `services/erp_stub` with internal ingress only (no external URL). When `erp_base_url` is empty, the adapter and reconciliation jobs use its internal FQDN, so dev has an ERP target without a real ERPNext instance. Set `erp_base_url` to point at a real ERP instead.

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
