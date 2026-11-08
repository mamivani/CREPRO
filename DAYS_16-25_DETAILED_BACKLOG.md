# Days 16-25 Backlog: Roadmap & Planning

**Status:** Ready for Development  
**Total Estimated Effort:** 10 days (can run in parallel with 2-3 person team)  
**Target Completion:** 2026-11-22 (2 weeks from Day 15)

---

## High-Level Overview

### What's Complete (Days 1-15)
✅ All infrastructure, authentication, property CRUD, ERP sync, reconciliation, CI/CD, testing, security

### What's Next (Days 16-25)
- Frontend with E2E tests (Day 16)
- Business logic: Lease, Utility, Maintenance, Reporting (Days 17-24)
- Production readiness: Multi-region, staging, monitoring (Day 25)

**Goal:** Fully functional property management platform with all MVP features, business logic, and production capabilities.

---

## Detailed Backlog

### Day 16: Next.js Frontend Scaffold + Playwright E2E Harness

**Objective:** Build UI framework with test automation from first commit (not bolted on later)

**Components:**

#### 16.1 Project Setup
- [ ] Create Next.js 14 project with TypeScript
- [ ] Configure Tailwind + ShadCN components
- [ ] Setup ESLint + Prettier
- [ ] Create folder structure (pages, components, hooks, services)
- [ ] Environment file template (.env.local.example)

#### 16.2 Layout & Navigation
- [ ] Root layout (header, sidebar, footer)
- [ ] Navigation menu with active link highlighting
- [ ] Responsive design (mobile/tablet/desktop)
- [ ] Dark mode toggle (Tailwind)
- [ ] User profile dropdown

#### 16.3 Authentication Pages
- [ ] Login page with OAuth provider buttons (Microsoft, Google, Apple)
- [ ] Local login fallback (username/password)
- [ ] Token storage (secure httpOnly cookie)
- [ ] Token refresh flow
- [ ] Logout functionality
- [ ] Redirect to dashboard on successful login
- [ ] 401 error handling for expired tokens

#### 16.4 Property Management Pages
- [ ] Property list page (table with search, sort, pagination)
- [ ] Property detail page (read-only view with audit trail)
- [ ] Property create form (name, address, type, units)
- [ ] Property edit form (update fields)
- [ ] Property delete confirmation
- [ ] Audit history view (change timeline)

#### 16.5 Invoice & Payment Pages
- [ ] Invoice list page (by property, with status)
- [ ] Invoice detail page (line items, customer, amount)
- [ ] Payment entry form (amount, date, method)
- [ ] Payment confirmation
- [ ] Payment history timeline

#### 16.6 Playwright E2E Test Suite
- [ ] `e2e.yml` CI workflow
- [ ] Login E2E tests
  - [ ] Microsoft OAuth flow
  - [ ] Google OAuth flow
  - [ ] Apple Sign-In flow
  - [ ] Local account login
  - [ ] Token refresh and re-authentication
- [ ] Property CRUD E2E tests
  - [ ] Create property from form
  - [ ] List properties with pagination
  - [ ] Edit property details
  - [ ] View audit trail
  - [ ] Delete property
- [ ] Invoice & Payment E2E tests
  - [ ] Create invoice in Property service
  - [ ] Verify invoice appears in ERP
  - [ ] Record payment in UI
  - [ ] Verify payment posts to ERP
  - [ ] Full flow: Property → Invoice → Payment → ERP
- [ ] Cross-browser testing (Chromium, Firefox, WebKit)
- [ ] HTML report generation on failure

#### 16.7 API Integration Layer
- [ ] HTTP client with axios + interceptors
- [ ] Token management (store, refresh, inject)
- [ ] Error handling (401, 403, 500)
- [ ] Request/response logging (dev mode)
- [ ] Environment-based API URLs

#### 16.8 State Management
- [ ] Context API for user/auth state
- [ ] Context API for tenant context
- [ ] Custom hooks (useAuth, useProperty, useInvoice)
- [ ] Session persistence across page reloads

**Exit Criteria:**
- [ ] Next.js app runs locally (`npm run dev`)
- [ ] All OAuth login flows work end-to-end
- [ ] Property CRUD functional through UI
- [ ] Playwright E2E tests pass (3 OAuth + local + CRUD + payment)
- [ ] CI `e2e.yml` workflow runs on every PR and passes
- [ ] Responsive on desktop, tablet, mobile
- [ ] Performance: Lighthouse score ≥ 90

**Files to Create:**
- `apps/web/` - Next.js application
- `apps/web/e2e/` - Playwright test suite
- `.github/workflows/e2e.yml` - CI workflow
- `playwright.config.ts` - Test configuration

**Testing:**
```bash
npm run dev  # Local dev
npx playwright test  # Run E2E tests
npm run build  # Production build
```

**Estimated Effort:** 5 days

---

### Days 17-18: Lease Service Business Logic

**Objective:** Implement complete lease domain model and workflows

**Components:**

#### 17.1 Lease Data Model
- [ ] Lease schema (property, tenant, start/end date, rent amount, security deposit)
- [ ] Lease status enum (draft, active, expired, terminated)
- [ ] Lease types (fixed-term, month-to-month)
- [ ] Renewal history tracking
- [ ] Database migrations

#### 17.2 Rent Increment Engine
- [ ] Annual increment algorithm (3% default, configurable)
- [ ] Increment application date (lease anniversary)
- [ ] Holdover rent calculation (month-to-month after expiry)
- [ ] Manual override capability
- [ ] Increment history audit trail
- [ ] Unit tests: 90%+ coverage

**Sample Logic:**
```python
def calculate_next_rent(current_rent: float, increment_pct: float) -> float:
    return current_rent * (1 + increment_pct / 100)

def apply_increment_to_lease(lease: Lease, effective_date: date):
    new_rent = calculate_next_rent(lease.rent_amount, lease.increment_percent)
    lease.rent_amount = new_rent
    lease.last_increment_date = effective_date
    lease.audit_log.append(f"Rent increased to {new_rent}")
    return lease
```

#### 17.3 Invoice Schedule Generation
- [ ] Generate invoices based on lease rent schedule
- [ ] Support multiple invoice frequencies (monthly, quarterly, semi-annual, annual)
- [ ] Handle pro-rata invoices (partial months at lease start/end)
- [ ] Scheduled job to generate invoices 30 days in advance
- [ ] Invoice posting to ERP via outbox

**Sample Logic:**
```python
def generate_lease_invoices(lease: Lease, start_date: date, end_date: date):
    invoices = []
    current_date = start_date
    while current_date <= end_date:
        invoice = Invoice(
            lease_id=lease.id,
            due_date=current_date + timedelta(days=15),
            amount=lease.rent_amount,
            period_start=current_date,
            period_end=current_date + timedelta(days=30)
        )
        invoices.append(invoice)
        current_date += timedelta(days=30)
    return invoices
```

#### 17.4 Payment Application
- [ ] Apply payments to invoices (full or partial)
- [ ] Track invoice balance
- [ ] Aging report (current, 30+, 60+, 90+ days)
- [ ] Automatic payment matching (AI-optional in Days 16+)
- [ ] Write-off capability with approval

#### 17.5 Lease Lifecycle
- [ ] Lease creation workflow
- [ ] Lease renewal workflow
- [ ] Lease termination workflow
- [ ] Eviction tracking (future: legal module)
- [ ] Move-out checklist and reconciliation

#### 17.6 Integrations
- [ ] Emit `lease.created` event to outbox
- [ ] Emit `lease.renewed` event
- [ ] Emit `lease.terminated` event
- [ ] ERP Customer linked to Lease tenant
- [ ] ERP Invoice posted on invoice generation

#### 17.7 Tests (90%+ coverage)
- [ ] Unit: Rent increment calculations (5 tests)
- [ ] Unit: Invoice schedule generation (4 tests)
- [ ] Unit: Payment application logic (6 tests)
- [ ] Integration: Lease CRUD with audit (4 tests)
- [ ] Integration: Invoice generation and posting (3 tests)
- [ ] Contract: OpenAPI schema compliance (2 tests)
- [ ] E2E: Create lease → generate invoices → record payment (1 test)

**Exit Criteria:**
- [ ] Lease service endpoints CRUD functional
- [ ] Rent increment engine tested and working
- [ ] Invoice schedule generates correctly for various lease terms
- [ ] Payments apply to invoices and update balance
- [ ] All events post to ERP correctly
- [ ] 90%+ test coverage
- [ ] No critical security or performance issues

**Files to Modify/Create:**
- `services/lease/` - Complete implementation
- `packages/crepro-common/src/models/lease.py` - Shared models

**Estimated Effort:** 2 days

---

### Days 19-20: Utility Billing Service

**Objective:** Implement utility metering and resident billing

**Components:**

#### 19.1 Meter Management
- [ ] Meter entity (unit, utility type, meter number, serial)
- [ ] Meter reading CRUD
- [ ] Meter status (active, inactive, replaced)
- [ ] Meter history (moves between units)

#### 19.2 Billing Calculation
- [ ] Usage calculation (current - previous reading)
- [ ] Rate table (per utility, per time period)
- [ ] Pro-rata adjustments (meter swap mid-period)
- [ ] Taxes and surcharges
- [ ] Minimum monthly charges

**Sample Logic:**
```python
def calculate_utility_charge(
    current_reading: float,
    previous_reading: float,
    rate_per_unit: float,
    minimum_charge: float = 0
) -> float:
    usage = max(0, current_reading - previous_reading)
    charge = usage * rate_per_unit
    return max(charge, minimum_charge)
```

#### 19.3 Resident Statements
- [ ] Monthly statement generation (email + UI download)
- [ ] Statement includes: usage, rate, charge, due date
- [ ] Statement posting to ERP as invoice line item

#### 19.4 Ledger & Reconciliation
- [ ] Utility ledger tracking (actual vs. billed)
- [ ] Variance investigation (over/under usage)
- [ ] Reconciliation with supplier invoices

#### 19.5 Tests (90%+ coverage)
- [ ] Unit: Usage calculations (6 tests)
- [ ] Unit: Rate application (4 tests)
- [ ] Integration: Meter CRUD + reading (3 tests)
- [ ] Integration: Statement generation (2 tests)
- [ ] Contract: API schema compliance (2 tests)

**Exit Criteria:**
- [ ] Meter endpoints working
- [ ] Usage calculations correct
- [ ] Statements generate and post to ERP
- [ ] 90%+ coverage

**Estimated Effort:** 2 days

---

### Days 21-22: Maintenance Dispatch Service

**Objective:** Work order and maintenance tracking

**Components:**

#### 21.1 Work Order Management
- [ ] Work order creation (resident request or internal)
- [ ] Assignment to maintenance staff
- [ ] Priority levels (urgent, normal, low)
- [ ] Status workflow (open → assigned → in-progress → completed → closed)
- [ ] Time tracking (hours worked)

#### 21.2 Cost Tracking
- [ ] Material costs
- [ ] Labor costs (hourly rate × hours)
- [ ] Total cost per work order
- [ ] Rollup to unit maintenance budget

#### 21.3 Photo & Document Storage
- [ ] Upload photos (before/after)
- [ ] Store in Azure Blob Storage
- [ ] Generate SAS URLs (time-limited access)
- [ ] Photo versioning

#### 21.4 Integrations
- [ ] Link work order to Property/Unit
- [ ] Post maintenance cost to ERP as expense
- [ ] Email notifications (staff assignment, completion)

#### 21.5 Tests (90%+ coverage)
- [ ] Unit: Cost calculations (4 tests)
- [ ] Integration: Work order CRUD (3 tests)
- [ ] Integration: Photo upload and retrieval (2 tests)
- [ ] Contract: API schema (2 tests)

**Exit Criteria:**
- [ ] Work order CRUD functional
- [ ] Photos stored and retrievable
- [ ] Costs tracked and posted to ERP
- [ ] 90%+ coverage

**Estimated Effort:** 2 days

---

### Days 23-24: Reporting & Analytics Service

**Objective:** Property financial dashboards and reports

**Components:**

#### 23.1 Dashboard Data Layer
- [ ] Optimized queries (indexed for fast retrieval)
- [ ] Read-only queries (no writes)
- [ ] Cache strategy (updated hourly for YTD, nightly for historical)

#### 23.2 Reports
- [ ] Property revenue dashboard (rent collected, utilities, fees)
- [ ] Occupancy report (units occupied, vacancy %, turnover)
- [ ] Receivables aging (current, 30+, 60+, 90+ days)
- [ ] Expense analysis (maintenance, utilities, admin)
- [ ] YTD/MTD financial summary

#### 23.3 Export Capabilities
- [ ] CSV export for all reports
- [ ] Excel export with formatting
- [ ] PDF generation for formal reports

#### 23.4 Scheduled Reports
- [ ] Email monthly summary to property manager
- [ ] Slack integration for alerts (high vacancy, high aging)

#### 23.5 Tests (80%+ coverage)
- [ ] Unit: Revenue calculation (3 tests)
- [ ] Integration: Dashboard queries (3 tests)
- [ ] Contract: Report API schema (2 tests)

**Exit Criteria:**
- [ ] Dashboard loads in <1 second
- [ ] All reports generate correctly
- [ ] Export works (CSV, Excel, PDF)
- [ ] 80%+ coverage

**Estimated Effort:** 2 days

---

### Day 25: Production Readiness & Multi-Region Staging

**Objective:** Prepare platform for production deployment

**Components:**

#### 25.1 Staging Environment
- [ ] Terraform clone (staging resource group `rg-crepro-staging`)
- [ ] Staging database (separate, non-production data)
- [ ] Staging Container Apps (same config as prod, different size)
- [ ] Staging DNS (staging.crepro.app, with test SSL cert)

#### 25.2 Failover & Disaster Recovery
- [ ] Database backup automation (daily, 30-day retention)
- [ ] Backup restoration procedure (tested)
- [ ] RTO/RPO targets documented (e.g., 4-hour RTO, 1-hour RPO)
- [ ] Failover runbook (step-by-step procedures)

#### 25.3 Monitoring & Alerting
- [ ] Azure Monitor dashboards (CPU, memory, latency, errors)
- [ ] Alert rules (high error rate, high latency, DLQ backlog)
- [ ] Notifications to Slack/email
- [ ] Service health status page

#### 25.4 Security & Compliance
- [ ] Production secret rotation (quarterly for JWT_SECRET, ERP credentials)
- [ ] Data residency compliance (all data in US region)
- [ ] Encryption at rest and in transit (enabled by default)
- [ ] Audit log retention policy (90 days min, 1 year preferred)
- [ ] Access control (production access limited to ops team)

#### 25.5 Performance Optimization
- [ ] Database query analysis (slow query log)
- [ ] Index optimization
- [ ] Connection pool tuning
- [ ] Container resource requests/limits optimized
- [ ] CDN for static assets (if applicable)

#### 25.6 Load Testing
- [ ] Baseline performance (100 concurrent users)
- [ ] Stress test (up to 500 concurrent users)
- [ ] Endurance test (stable load for 2 hours)
- [ ] Results documented with scaling recommendations

#### 25.7 Final Checklists
- [ ] Security checklist (all controls in place)
- [ ] Operational checklist (monitoring, alerting, backups)
- [ ] Compliance checklist (GDPR, CCPA, SOC 2)
- [ ] Runbook completeness (troubleshooting for all common issues)

**Exit Criteria:**
- [ ] Staging environment deployable from Terraform
- [ ] Failover tested and documented
- [ ] Monitoring and alerting active
- [ ] Load test results show acceptable performance
- [ ] Production readiness sign-off

**Estimated Effort:** 1 day

---

## Parallel Work Streams

If team scales beyond 1 person, work streams can run in parallel:

### Stream 1 (Days 16-17): Frontend + Lease
- Developer 1: Next.js frontend scaffold (Day 16)
- Developer 2: Lease business logic (Days 17-18 start)

### Stream 2 (Days 17-18): Utilities + Maintenance
- Developer 3: Utility billing (Days 19-20 start)
- Developer 4: Maintenance dispatch (Days 21-22 start)

### Stream 3 (Days 23-24): Analytics + Staging
- DevOps: Staging setup + monitoring (Day 25 start)
- Developer 5: Reporting service (Days 23-24)

**Synchronization Points:**
- Day 18 end: All services merged to main
- Day 22 end: All business logic complete, integration testing
- Day 24 end: Performance testing + production readiness review

---

## Dependency Tracking

```
Day 16 (Frontend)
  ↓ Depends on Days 1-15 (complete)
  
Day 17-18 (Lease)
  ↓ Depends on Day 16 (frontend for E2E)
  
Day 19-20 (Utilities)
  ↓ Depends on Day 17-18 (shared domain patterns)
  
Day 21-22 (Maintenance)
  ↓ Depends on Day 19-20 (shared patterns)
  
Day 23-24 (Reporting)
  ↓ Depends on Day 21-22 (all services ready for analysis)
  
Day 25 (Production)
  ↓ Depends on Days 23-24 (complete, stabilized system)
```

---

## Definition of Done (Per Day)

- [ ] All code committed to `develop` and merged to `main`
- [ ] All tests passing (80%+ coverage minimum)
- [ ] CodeQL, Dependabot, secret scanning passing
- [ ] Container images built and scanned (0 critical CVEs)
- [ ] Documentation updated (README, architecture, deployment, runbook)
- [ ] E2E tests passing (if frontend-related)
- [ ] Manual smoke tests verified in Dev environment
- [ ] Demo recorded or documented

---

## Known Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| OAuth provider rate limits during testing | Medium | High | Cache tokens, use test accounts |
| Database performance with large reports | Medium | High | Pre-compute dashboards, use read replicas (Day 25) |
| Image upload failures (network timeouts) | Low | Medium | Retry logic, max file size validation |
| Multi-region complexity | Low | High | Start with one region, add second in Day 25 follow-up |
| Scope creep (more business logic) | High | High | Strict backlog prioritization, sprint goals |

---

## Success Metrics

By end of Day 25:

1. **Functional:** All MVP features working (lease, utility, maintenance, reporting)
2. **Tested:** 90%+ test coverage across all services
3. **Secure:** All security scans passing, 0 critical findings
4. **Performant:** Dashboard loads in <1s, API responses <100ms
5. **Documented:** Complete runbooks and architectural documentation
6. **Production-ready:** Staging environment live, failover tested

---

**Backlog Ready for Development**  
**Expected Completion:** 2026-11-22 (2 weeks from Day 15)  
**Team Size:** 1 (sequential) or 3-5 (parallel, recommended)
