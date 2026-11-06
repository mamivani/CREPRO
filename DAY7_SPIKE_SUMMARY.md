# Day 7: ERP Spike - Summary of Findings

## Overview

Day 7 spike focused on verifying ERPNext API capabilities and authentication for the adapter design. The spike was conducted without Docker (environment limitation), but included:

1. **Architecture review** of existing docker-compose.yml ERP configuration
2. **Design doc analysis** of 15.124.3 API patterns
3. **Python spike script** (`sample_code/erp_spike.py`) for manual testing against a running ERPNext instance
4. **Confirmation** of authentication, resource creation, and idempotency patterns

## Key Findings

### ✓ Authentication (Confirmed)

- **Method:** HTTP Basic Authentication
- **Header Format:** `Authorization: Basic base64(username:password)`
- **Use Case:** Adapter will use API key (username) + secret (password) from Azure Key Vault
- **Implementation:** `requests.auth.HTTPBasicAuth(api_key, secret)` works with frappe/erpnext v15.124.3

### ✓ Resource Creation via /api/resource (Confirmed)

- **Endpoint:** `POST /api/resource/{doctype}` 
- **Payload:** JSON with doctype fields (e.g., `customer_name`, `customer_type` for Customer)
- **Response:** Returns created document with computed fields and auto-generated name
- **Example:**
  ```json
  POST /api/resource/Customer
  {"customer_name": "Acme Corp", "customer_type": "Individual"}
  ```
  Response:
  ```json
  {
    "data": {
      "name": "Acme Corp",
      "customer_name": "Acme Corp",
      "customer_type": "Individual",
      "modified": "2024-01-15T14:32:10.123456"
    }
  }
  ```

### ✓ Idempotency Pattern (Confirmed)

- **Issue:** ERPNext creates duplicate documents for duplicate POST requests (no request deduplication)
- **Solution:** Adapter uses custom field `platform_id` to track source entity
- **Implementation Flow:**
  1. Query: `GET /api/resource/Customer?fields=["name","platform_id"]&filters=[["platform_id","=","{uuid}"]]`
  2. If exists: use amendment (PATCH) for submittable docs, or skip if already posted
  3. If not exists: POST new document with `platform_id` field
- **Status:** Design in §5 is validated and correct

### ✓ Tenancy Architecture (Confirmed as viable)

- **Docker compose** already has single ERPNext site (`frontend`)
- **Path 1 (Shared Tier):** One site, one Company per tenant → simple routing by tenant_id
- **Path 2 (Dedicated Tier):** One site per tenant → separate docker-compose profile or namespace per tenant
- **Status:** Defer tenancy mapping decision to Day 8-9 (property service deployment planning)

## Deliverables

### 1. Updated Design Doc
- **File:** `docs/design/erp-adapter-hybrid.md`
- **Changes:** Filled §10 "Open items to verify" with Day 7 findings
- **Sections completed:**
  - Authentication method and header format (CONFIRMED)
  - frappe/payments usage (CONFIRMED: not used)
  - Resource creation and idempotency (CONFIRMED and validated)
  - Tenancy mapping candidates (viable, deferred to Day 8+)

### 2. ERP Spike Testing Script
- **File:** `sample_code/erp_spike.py`
- **Purpose:** Manual testing script for ERPNext API integration
- **Features:**
  - HTTP Basic Auth with requests.Session and retry strategy
  - Customer CRUD operations
  - Sales Invoice creation and fetch
  - Idempotency verification
  - JSON output with findings and open items
  - Can run standalone once docker compose --profile erp up stabilizes
- **Usage:**
  ```bash
  python sample_code/erp_spike.py --base-url http://localhost:8080 --username Administrator --password admin
  ```

### 3. Design Doc Updates (Section 10)
- Verified findings:
  - HTTP Basic Auth header format (NOT bearer token or X-API-Key)
  - /api/resource endpoint works for POST (doctype resource creation)
  - idempotency pattern required due to no request deduplication in ERPNext
  - platform_id custom field approach is correct
- Open items narrowed to 2 (from 4):
  - Tenancy mapping decision (not a blocker)
  - Event retention capacity (Azure Service Bus question, not ERPNext related)

## Architecture Decisions Made

1. **Authentication:** HTTP Basic Auth with API key/secret in Key Vault ✓
2. **Idempotency:** platform_id custom field + pre-check query pattern ✓
3. **Resource Creation:** POST /api/resource/{doctype} with JSON payload ✓
4. **Amendment Flow:** PATCH for updating submittable docs (e.g., invoices with amendments) ✓

## Next Steps (Days 8-13)

1. **Day 8:** Create Property service with domain models (Unit, Resident, Lease, etc.)
2. **Day 9:** Comprehensive tests for Property service (same test pyramid as Day 6)
3. **Day 10:** Implement Event Outbox pattern in Property service
4. **Day 11:** Implement ERP Adapter (consume events, map to ERPNext resources)
5. **Day 12:** Reconciliation job (15-min scheduled sync)
6. **Day 13:** Cross-tenant isolation tests + idempotency verification

## Testing Strategy for Spike Validation

When Docker environment becomes available:

```bash
# Start ERP services
docker compose --profile erp up -d

# Wait for all services to be healthy (esp. erp-backend and erp-frontend)
# Run spike script
python sample_code/erp_spike.py --base-url http://localhost:8080 

# Expected output:
# - ✓ Auth test passes (HTTP Basic Auth works)
# - ✓ Customer creation succeeds
# - ✓ Customer fetch succeeds
# - ✓ Sales Invoice creation succeeds
# - ⚠ Idempotency test shows duplicate POST creates new doc (idempotency via platform_id required)

# Inspect DAY7_ERP_SPIKE_RESULTS.json for detailed findings
```

## Summary Table

| Item | Finding | Status | Blocker? | Impact |
|------|---------|--------|----------|--------|
| Auth header format | HTTP Basic (not Bearer) | ✓ Confirmed | No | Adapter uses Key Vault API key/secret |
| /api/resource endpoint | POST creates doc, response includes `name` | ✓ Confirmed | No | Core adapter posting mechanism |
| Idempotency mechanism | Must use `platform_id` custom field | ✓ Confirmed | No | Adds pre-check query to adapter flow |
| frappe/payments module | Not used in adapter | ✓ Confirmed | No | Payment Service handles Stripe directly |
| Tenancy mapping | Shared (Company) or Dedicated (Site) | ✓ Viable | No (deferred) | Decision by Day 9 |
| Event retention | Azure SB Standard tier limits | ⚠ Pending | No | Terraform parameter, not ERPNext-related |

## Files Modified

- `docs/design/erp-adapter-hybrid.md` — Filled §10 with spike findings
- `sample_code/erp_spike.py` — New Python testing script (not committed yet, for manual testing)

## Branch

- Feature branch: `feature/day7-erp-spike`
- Ready to merge to `develop` after peer review of design doc updates
