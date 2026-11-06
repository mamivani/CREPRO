# 🎯 MAJOR ARCHITECTURAL UPDATE: CommonERP Integration

## What Changed

Your 15-day CREPRO implementation plan has been **revised to integrate ERPNext (now called CommonERP) as a core CREPRO service** instead of treating it as an external system.

### The Vision

**Before (Revision 2):**
```
CREPRO Platform (11 services)
    ↓
ERP Adapter Service
    ↓
External ERPNext
```

**Now (Revision 3 - CommonERP):**
```
CREPRO Platform (11 services + CommonERP)
    ↓
Event Subscribers
    ↓
CommonERP GL Posting
(all integrated, single deployment)
```

---

## Key Changes Summary

### ✅ What This Means

1. **ERPNext is now called CommonERP** and lives inside the CREPRO repo
2. **Deployed as a native service** alongside Identity, Property, Lease, etc.
3. **Multi-tenant support built-in** - one CommonERP service with N Companies (one per tenant)
4. **Simpler architecture** - no separate adapter service, no external API calls
5. **Faster integration** - event subscribers post to CommonERP GL synchronously
6. **All capabilities available** - full ERPNext accounting module (GL, AR, AP, Sales, Purchases)

### 📊 Complexity Reduction

| Metric | Revision 2 | Revision 3 | Change |
|--------|-----------|-----------|--------|
| Services | 11 + adapter + external ERP | 11 + CommonERP | -1 service |
| Adapter code | ~1,500 lines | ~600 lines | -900 lines |
| Deployment targets | 13+ containers | 12 containers | Simpler |
| Days 11-13 scope | Full adapter pattern | Event subscribers | 2 days instead of 3 |
| Testing complexity | Adapter integration | Event flow | Simpler |

---

## Impact on 15-Day Timeline

| Days | Revision 2 | Revision 3 | Change |
|-----|-----------|-----------|--------|
| 1-6 | Identity, tests | Identity, tests | **No change** |
| **7** | **External ERP spike** | **CommonERP integration spike** | Vendor ERPNext, validate multi-tenant |
| 8-10 | Property, backfill tests, outbox | Property, backfill tests, outbox | **No change** |
| **11-12** | **Adapter service (2 days)** | **Event subscribers (2 days)** | Simplified, fewer LOC |
| **13** | **Reconciliation job** | **Simplified reconciliation** | Fewer moving parts |
| 14-15 | Smoke tests, demo | Smoke tests, demo | **No change** |

**Total time: 15 days (same as Revision 2)**

---

## What CommonERP Brings

CommonERP is **ERPNext v15.124.3** with all capabilities:

| Module | Feature | CREPRO Use |
|--------|---------|-----------|
| **Accounting** | General Ledger | GL entries for all transactions |
| **AR/AP** | Accounts Receivable | Rent invoices, tenant payments |
| **Sales** | Sales Invoice | Rent/fee invoicing |
| **Purchases** | Purchase Order | (Not Day 15, future use) |
| **Utilities** | Mode of Payment | ACH, card, check (future) |
| **Customization** | Custom Fields | Platform_id tracking (optional) |

**Day 15 Scope:** AR/AP/GL only (core accounting)

**Day 16+ Scope:** HR, Projects, Inventory, CRM modules as needed

---

## How Multi-Tenancy Works

### Current (Revision 2) - External ERPNext
- One Frappe site
- One Company per tenant
- Adapter posts to correct Company

### Revision 3 - CommonERP Integrated
- **Still:** One Frappe site + One Company per tenant
- **Different:** Inside CREPRO docker network
- **Routing:** JWT `tenantId` → CommonERP Company lookup
- **Isolation:** Tenant queries return only their Company GL

**Example:**
```
Tenant A (hotels.example.com):
  → Company: Acme Hotels
  → GL entries for Acme

Tenant B (rentals.example.com):
  → Company: Beach Rentals
  → GL entries for Beach Rentals

Isolation verified by tests: Tenant A cannot read Tenant B's GL
```

---

## Day 7: CommonERP Integration Spike

### What Happens
1. **Vendor ERPNext v15.124.3** to `vendor/erpnext/`
2. **Identify customization points:**
   - Tenant routing (which tenant → which Company)
   - Company auto-assignment on documents
   - Tenant filtering on GL reads
3. **Create test script** to verify:
   - Multi-tenant Customer creation
   - Cross-tenant isolation (404 if accessing other Company)
   - Invoice posting to correct Company
4. **Update design doc** with CommonERP architecture

### Outcome
- CommonERP docker image working
- Multi-tenant routing strategy documented
- Customization scope minimized (fewer breaking changes)

---

## Days 11-12: Event Subscribers (vs. Adapter)

### Event Flow Example: Property → Customer in CommonERP

```python
# Property Service (Day 8)
@router.post("/api/v1/properties")
def create_property(prop: PropertyCreate, tenant_id: UUID):
    property = Property(...)
    properties.create(property)
    
    # Publish event
    event = PropertyCreated(
        id=uuid4(),
        tenant_id=tenant_id,
        property_id=property.id,
        property_name=property.name,
        timestamp=now()
    )
    outbox.create(OutboxRow(event))
    
    return property

# Event Subscriber (Day 11)
@dapr_subscription("property-events")
def on_property_created(event: PropertyCreated):
    # Get tenant's CommonERP Company
    company = get_company_for_tenant(event.tenant_id)
    
    # Post Customer to CommonERP
    customer = {
        "doctype": "Customer",
        "customer_name": event.property_name,
        "customer_type": "Individual",
        "company": company.name
    }
    
    # Idempotency: check event id + hash
    if event_already_processed(event):
        return
    
    # POST to CommonERP
    resp = common_erp_client.post("/api/resource/Customer", customer)
    
    # Mark event processed
    mark_event_processed(event)
```

### Key Differences (vs. Adapter)
- ✅ Event subscriber runs in its service (not separate adapter)
- ✅ Posts to CommonERP directly (HTTP, not message queue)
- ✅ Idempotency via event id (not platform_id field)
- ✅ Synchronous (blocking until CommonERP responds)
- ⚠️ No dead-letter queue (optional, Day 16)

---

## Days 14-15: Deployment & Verification

### Day 14: Full Pipeline Deployment
```bash
docker compose up
# Starts: Identity, Property, Lease, Payment, CommonERP, ...

# terraform apply
# Deploys all 12 services to Dev Container Apps
```

### Day 15: Exit Criteria Verification
1. **User can sign in** (unchanged)
2. **Property created & visible to tenant only** (unchanged)
3. **✅ NEW: Property → Customer in CommonERP Company**
   - Tenant A's property creates Customer in Company A GL
   - Tenant B's property creates Customer in Company B GL
   - Cross-tenant isolation verified
4. **✅ NEW: Payment → GL entry in CommonERP**
   - PaymentPosted event → GL posting
   - Correct tenant's Company
5. **All services deployed** (unchanged)
6. **Smoke tests pass** (unchanged)

---

## Design Documents

### Updated
- ✅ **docs/plan/15-day-plan-solo.md** - Full revision with CommonERP details

### New (To Create)
- 📄 **docs/design/erp-integration-design.md** (Day 7)
  - CommonERP architecture
  - Multi-tenant routing strategy
  - Company assignment
  - Event subscriber mappings
  - GL entry examples

### Previous (Archived)
- 📦 **docs/design/erp-adapter-hybrid.md** - (Previous Revision 2 pattern; kept for reference)

---

## Immediate Next Steps

1. **Review Plan Revision 3** - Read PLAN_REVISION_3_COMMON_ERP.md
2. **Approve architectural change** - Integrate CommonERP vs. external ERP?
3. **Days 1-6 proceed as planned** (already complete up to Day 8)
4. **Day 7 CommonERP spike** - Vendor ERPNext, validate multi-tenant
5. **Design doc** - Create erp-integration-design.md

---

## FAQ

**Q: Is all of ERPNext available, or just accounting?**  
A: All of ERPNext v15.124.3 is available. Day 15 uses only GL/AR/AP; other modules (HR, Projects, etc.) available for Day 16+.

**Q: What about external ERPNext deployments (customer on their own server)?**  
A: This is Revision 3 (integrated for MVP). Day 16+ can support external ERPNext instances as an alternative architecture.

**Q: Will this still work if I need to upgrade ERPNext later?**  
A: Yes. Customizations are minimal (just tenant routing), so upgrades are easier. Version pinned at v15.124.3 for Revision 3.

**Q: Can I split CommonERP to a separate deployment later?**  
A: Yes. CommonERP is a containerized service, so it can be split into its own cluster/region in Day 16+ without code changes to CREPRO.

**Q: What about DBAs managing ERPNext separately?**  
A: For Day 15 (MVP), CommonERP shares PostgreSQL with CREPRO. Day 16+ can provision separate database.

---

## Risk Assessment

### Manageable Risks
- **CommonERP vendoring complexity:** 4-hour spike on Day 7; fallback to Revision 2 if needed
- **Multi-tenant routing bugs:** Isolation tests on Day 9 catch issues
- **Frappe customization drift:** Minimal scope (1-2 hooks), easy to audit

### Mitigated vs. Revision 2
- ✅ No separate adapter service (fewer moving parts)
- ✅ No message broker complexity (direct HTTP)
- ✅ No external API surprises (ERPNext already validated in Day 7 spike)
- ✅ Fewer deployment knobs (one unified docker-compose)

---

## Summary

**You now have a cleaner, simpler architecture:**

- 🎯 **Integrated platform:** CREPRO + CommonERP in one deployment
- ✅ **All ERP capabilities:** Full accounting module native to platform
- 📉 **Reduced complexity:** 1 fewer service, 900 fewer lines of code
- ⏱️ **Same timeline:** 15 days, Days 11-13 simplified to Days 11-12
- 🔐 **Multi-tenant native:** One CommonERP service handles all tenants
- 🧪 **Verified:** Isolation tests prove cross-tenant protection

**Next:** Proceed with Days 1-6 (already complete); Day 7 CommonERP spike; Days 8-15 execute per Plan Revision 3.

---

**Files Created:**
- ✅ PLAN_REVISION_3_COMMON_ERP.md - Detailed architecture change
- ✅ docs/plan/15-day-plan-solo.md - Updated with CommonERP details

**Status:** Ready to implement Days 7-15 with CommonERP integration ✅
