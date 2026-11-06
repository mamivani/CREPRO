# 15-Day Plan Revision 3: CommonERP Integration

## Executive Summary

**Major Architectural Change:** ERPNext is now integrated as a **core CREPRO service** (renamed CommonERP) instead of an external system.

- **Previous architecture (Revision 2):** CREPRO property management platform → ERP Adapter → external ERPNext (separate service)
- **New architecture (Revision 3):** Unified CREPRO platform combining property management + embedded CommonERP (ERPNext v15.124.3)

**Impact on 15-day plan:**
- Days 1-6: Unchanged (repo setup, dockerization, Terraform, security gates, Identity, testing)
- Days 7-15: Simplified (CommonERP is now native, not external; no separate adapter service; event-driven GL posting instead of message-based adapter)
- Deliverable complexity: Reduced (fewer services, simpler integration, faster testing)
- Exit criteria: Same (GL postings verified, multi-tenant isolation verified, end-to-end pipeline)

---

## What Changed

### Scope Change: In vs. Out

**NEW IN (Revision 3 only):**
- CommonERP (ERPNext v15.124.3) as a core CREPRO service
- Vendor ERPNext under `vendor/erpnext/` with multi-tenant customizations
- CommonERP Container App deployed alongside Identity, Property, etc.
- CommonERP database/site provisioning via Terraform (Day 3)
- Event subscribers that post to CommonERP GL (Days 11-12)
- CommonERP multi-tenant isolation tests (Day 9)

**REMOVED (vs. Revision 2):**
- ERP Adapter service (was Day 11-13)
- Adapter ledger table (no longer needed)
- Dead-letter queue processing (simplified to event dedup)
- Reconciliation job reading external ERP (nightly full pass still exists, but simpler)
- External ERP service deployment (CommonERP is now internal)

**REMAINS SAME:**
- Identity OAuth (Days 5-6)
- Property service (Days 8-9)
- Event outbox + relay (Days 10)
- Testing strategy (Days 6, 9, 14-15)
- Terraform for Azure (Days 3, 14)
- CI/CD pipeline (Days 4, 14)

---

## Day-by-Day Changes

### Day 7: CommonERP Spike (vs. External ERP Spike)

**Revision 2 (External ERP Spike):**
- Create API key on external site
- Verify HTTP header format
- Post Customer/Invoice via REST API
- Record API design in docs

**Revision 3 (CommonERP Integration Spike):**
- Vendor ERPNext v15.124.3 under `vendor/erpnext/`
- Identify multi-tenant customization points:
  - Tenant routing (which Company for which tenant)
  - Company assignment on documents (auto-bind from JWT)
  - Tenant filtering on reads (visibility controls)
- Create spike script to test:
  - Multi-tenant API key + HTTP Basic Auth
  - Customer creation in Tenant A's Company
  - Customer creation in Tenant B's Company (verify isolation)
  - Invoice posting to correct Company
  - Cross-tenant read attempts return 404 (isolation)
- Update design doc (erp-integration-design.md) with CommonERP architecture

**Outcome:** CommonERP docker image in local `docker-compose.yml`, provisioned site, multi-tenant routing strategy documented

### Days 8-9: Property Service + Tests (Same as Revision 2)

- Day 8: Create Property API, publish PropertyCreated event
- Day 9: Backfill CRUD + isolation tests for 11 services
  - NEW: CommonERP tests verify GL posting and Company isolation

### Day 10: Outbox + Event Relay (Same as Revision 2)

- Property/Lease/Payment publish events to Service Bus topics
- No external ERP topic; events stay internal to CREPRO

### Days 11-12: Event-Driven GL Posting (vs. Adapter Pattern)

**Revision 2 (Adapter Pattern - Days 11-13):**
- Day 11: Adapter subscribes to `erp-events` topic
- Day 12: Adapter maps events to doctype fields (Customer, Invoice, Payment Entry)
- Day 13: Reconciliation job scans for missing/mismatched records

**Revision 3 (Event Subscribers - Days 11-12):**
- Day 11: Event subscribers (Python/FastAPI) in services or common_erp_service
  - PropertyCreated → POST /api/resource/Customer (CommonERP)
  - LeaseExecuted → POST /api/resource/Sales Invoice
  - PaymentPosted → POST /api/resource/Payment Entry + GL posting
  - Idempotency: event id + payload hash (application level)
- Day 12: Retry policy (5 attempts, back-off), poison message handling
  - Failed events logged/alerted; manual replay after fix
  - Tests: duplicate event creates one record; malformed event logged

**Outcome:** Property → Customer in CommonERP; Lease/Payment GL entries posted; all multi-tenant isolation verified

### Day 13: Reconciliation Simplified (vs. Revision 2)

**Revision 2:**
- Scan external ERP; compare with platform
- Re-post missing records to external ERP

**Revision 3:**
- Nightly full pass compares Property/Lease/Payment with CommonERP GL
- Re-post missing GL entries (query CommonERP for gaps)
- Simpler scope (no adapter ledger, no platform_id field on ERP docs, internal query language)

### Day 14: Deployment (Slight Change)

**Revision 2:**
- Deploy 11 services + ERP Adapter + Reconciliation Job + external ERP
- 13+ containers

**Revision 3:**
- Deploy 11 services + CommonERP + Reconciliation Job
- 12 containers (CommonERP replaces separate adapter/external-erp)
- CommonERP site provisioning via Terraform/post-deploy script

### Day 15: Demo & Docs (Minor Change)

- All services deployed
- CommonERP GL entries verified for Property/Lease/Payment events
- No "external ERP" to demo; CommonERP is native
- Design doc: erp-integration-design.md (replaces erp-adapter-hybrid.md)

---

## Architecture Comparison

| Component | Revision 2 | Revision 3 |
|-----------|-----------|-----------|
| **ERP System** | External (frappe/erpnext in docker-compose) | Integrated (CommonERP in services/) |
| **API Integration** | ERP Adapter service (separate container) | Event subscribers (part of other services) |
| **Database** | Separate MariaDB + Redis for external ERP | Shared PostgreSQL (CommonERP schema) |
| **Service Count** | 11 + adapter + external ERP = 13+ | 11 + CommonERP = 12 |
| **Event Flow** | Property → Service Bus → Adapter → external ERP | Property → Service Bus → subscriber → CommonERP HTTP |
| **Idempotency** | platform_id field on external ERP docs | event id + payload hash in application |
| **Multi-tenancy** | One site + N Companies (or N sites) | One CommonERP service + N Companies |
| **Reconciliation** | Reads external ERP; re-posts via adapter | Reads CommonERP GL; re-posts GL entries |
| **Testing Scope** | Adapter integration (11 tests/service + adapter) | Event flow (11 tests/service + CommonERP) |
| **Deployment** | Separate ERP docker-compose profile | Native Container App with site provisioning |

---

## Key Design Decisions (Revision 3)

### 1. Multi-Tenancy Strategy
- **One CommonERP service** + N Frappe Companies (one per tenant)
- **Routing layer:** JWT `tenantId` → query CommonERP Company for that tenant
- **Company assignment:** Auto-bind on document creation from JWT
- **Tenant filtering:** All reads filtered by authorized Company (via JWT)

### 2. Event-Driven Posting vs. Message Broker
- **Decision:** Event subscribers post to CommonERP **synchronously** (not via separate adapter)
- **Why:** Simpler, fewer services, immediate feedback on GL posting
- **Trade-off:** Events block until CommonERP posts; timeout if CommonERP down (acceptable for Day 15)
- **Future (Day 16+):** Async posting with dead-letter queue if throughput needed

### 3. Data Ownership
- **Tenants create properties/leases/payments in CREPRO** (Property/Lease/Payment services)
- **GL entries live in CommonERP** (read from CommonERP for reports/audit)
- **CREPRO is system of record for operations**, CommonERP for accounting
- **No two-way sync:** Platform changes do not update CommonERP (GL is append-only)

### 4. Customization Scope
- **Minimal:** Only tenant routing + Company assignment hooks
- **No vendoring large amounts of Frappe code** (use standard v15.124.3 image)
- **Hooks:** One or two custom functions in `vendor/erpnext/customizations/` for multi-tenant logic
- **Risk:** Standard ERPNext updates may break customizations (mitigated by testing, small scope)

### 5. Deployment & Provisioning
- **Terraform** (Day 3): Creates CommonERP database + site config
- **Post-deploy script:** Runs `bench` commands to set up site (admin user, Companies, etc.)
- **Or:** Docker entrypoint provisioning (simpler but less idempotent)

---

## Testing Strategy (Revision 3)

### Test Coverage (Day 9)

| Service | Tests | Focus |
|---------|-------|-------|
| Property | 15-20 | CRUD, tenant isolation, PropertyCreated event |
| Lease | 15-20 | CRUD, tenant isolation, LeaseExecuted event |
| Payment | 15-20 | CRUD, tenant isolation, PaymentPosted event |
| CommonERP | 15-20 | Multi-tenant Company isolation, GL posting, event subscription |
| Other 7 services | 10-15 each | CRUD, tenant isolation |

### CommonERP-Specific Tests

**Multi-Tenant Isolation:**
- Tenant A creates Property → CommonERP Customer in Company A
- Tenant B creates Property → CommonERP Customer in Company B
- Tenant A queries CommonERP → sees only Company A customers (404 for Company B)
- Tenant B cannot write to Company A (authorization error)

**Event Flow:**
- Property service publishes PropertyCreated event
- CommonERP subscriber receives event
- CommonERP creates Customer in tenant's Company
- Duplicate event (same event id) → no duplicate Customer

**GL Posting:**
- PaymentPosted event → CommonERP creates Payment Entry + GL postings
- GL postings in correct Company
- Tenant A's GL separate from Tenant B's

---

## Impact on Exit Criteria (Day 15)

### Original (Revision 2):
- ✅ User signs in (unchanged)
- ✅ Property created + visible to tenant only (unchanged)
- **Property/Payment appear in external ERP exactly once**
- **Dead-lettered event replayed by reconciliation**
- ✅ 11 services + adapter containerized
- ✅ Smoke tests pass

### Revised (Revision 3):
- ✅ User signs in (unchanged)
- ✅ Property created + visible to tenant only (unchanged)
- **Property → Customer in CommonERP Company A (Tenant A), Company B (Tenant B)**
- **Payment → GL entry in CommonERP Company (correct tenant)**
- **Event posted exactly once (application-level dedup)**
- ✅ 11 services + CommonERP containerized
- ✅ Smoke tests pass

**Net result:** Same validation, simpler architecture

---

## Risk Assessment (Revision 3)

### New Risks (vs. Revision 2)

| Risk | Likelihood | Mitigation |
|------|------------|-----------|
| CommonERP vendoring takes longer than Day 7 allows | Medium | Scope Day 7 to 4 hours; if slip, defer CommonERP to Day 16 + use Revision 2 adapter pattern |
| Multi-tenant routing bugs in CommonERP customizations | Medium | Isolation tests on Day 9; manual verification in smoke tests |
| Synchronous event posting blocks if CommonERP slow | Low | Acceptable for Day 15 (demo); async optional in Day 16 |
| Frappe customization breaks on v15 update | Low | Pin v15.124.3; audit customization scope (minimal) |

### Reduced Risks (vs. Revision 2)

- ✅ No separate adapter service (fewer components to test/deploy)
- ✅ No message broker complexity (DLQ, reconciliation simpler)
- ✅ No external API surprises (ERPNext already spiked)
- ✅ Fewer deployment knobs (one fewer docker-compose profile)

---

## Impact on Scope & Complexity

### Services Count
- **Revision 2:** 11 CREPRO services + 1 adapter + 1 external ERP = 13+
- **Revision 3:** 11 CREPRO services + 1 CommonERP = 12
- **Reduction:** 1 service, simpler orchestration

### Code Changes (Relative)
- **Revision 2:** Days 11-13 = 3 days × (~500 lines/day) = 1,500 lines adapter
- **Revision 3:** Days 11-12 = 2 days × (~300 lines/day) = 600 lines subscribers
- **Reduction:** 900 lines of adapter code; moved CommonERP logic to event subscribers

### Test Changes
- **Revision 2:** Adapter tests + external ERP contract tests
- **Revision 3:** Event flow tests + CommonERP GL verification
- **Net:** Similar test count, different focus

### Deployment Complexity
- **Revision 2:** Separate docker-compose profile; external ERP Terraform resource
- **Revision 3:** CommonERP as native Container App; Terraform site provisioning
- **Net:** Simpler (one fewer "special" resource)

---

## Handoff to Days 16-25

### Refinements for Production
1. **Async event posting** (queue + retry, not sync)
2. **CommonERP schema versioning** (handle upgrades)
3. **Reporting** (GL reports, AR/AP aging, audit trail)
4. **Stripe integration** (Payment Entry ↔ Stripe webhooks)
5. **Lease business logic** (rent increment, invoice schedule)

### Open Questions for Day 16+
1. Is one CommonERP site per tenant (dedicated tier) needed, or is Company-per-tenant sufficient?
2. How to handle CommonERP data in multi-region DR (CREPRO in region A, CommonERP backup in region B)?
3. Audit trail: store all GL postings as immutable events, or rely on CommonERP Journal Posting?

---

## Summary

**Revision 3 simplifies CREPRO architecture** by integrating CommonERP as a core service rather than treating ERPNext as an external system. This reduces:
- Service count by 1
- Adapter complexity by ~900 lines
- Testing scope (event flow vs. full adapter lifecycle)
- Deployment knobs (fewer profiles/special cases)

**Trade-offs:**
- Synchronous event posting (OK for Day 15, can be made async in Day 16)
- Tight coupling between CREPRO and ERPNext versions (mitigated by minimal customizations)
- Learning curve for Frappe customization (Day 7 spike mitigates)

**Exit Criteria:** Same as Revision 2 (GL verified, multi-tenant isolated, end-to-end pipeline)

**Timeline:** Days 1-6 unchanged; Days 7-15 use CommonERP instead of Adapter pattern; total days = 15 (no change)

---

## Files to Update (Revision 3)

### Design & Planning
- ✅ `docs/plan/15-day-plan-solo.md` (this document)
- 📝 `docs/design/erp-integration-design.md` (NEW: replaces erp-adapter-hybrid.md)
  - Multi-tenant CommonERP architecture
  - Company assignment strategy
  - Event posting flow
  - GL entry mappings

### Code Structure (Days 7-15)
- 📁 `vendor/erpnext/` (NEW: vendored ERPNext + customizations)
- 📁 `services/common_erp_service/` (NEW or use existing erp_adapter/)
  - Event subscribers
  - CommonERP HTTP client
  - GL posting logic
- ✏️ `docker-compose.yml` (update ERP section: rename to CommonERP, add site provisioning)
- ✏️ `infra/terraform/` (update: CommonERP site provisioning)

### Testing
- 📁 `services/common_erp_service/tests/` (NEW: multi-tenant isolation + GL posting)
- ✏️ `services/property/tests/` (update: PropertyCreated event publishing)

---

*Plan Revision 3 - Integrated CommonERP*  
*Status: Ready for implementation (Days 7-15)*  
*Previous Revisions: Revision 1 (3-service MVP), Revision 2 (11 services + external adapter)*
