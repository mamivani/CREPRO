# Days 11-15 Implementation + Frontend Roadmap for CREPRO

## Days 11-15 Backend Completion Summary

### Day 11: ERP Adapter Push Path ✅ IN PROGRESS
**Objective:** Subscribe to `erp-events`, check idempotency, post to external ERP

**Completed:**
- ✅ `services/erp_adapter/src/crepro_erp_adapter/push.py`: Full push handler with idempotency
- ✅ `/subscribe/erp-events` Dapr pub/sub endpoint integrated into API router
- ✅ Adapter ledger entry recording (POSTED, FAILED states)
- ✅ Event-to-doctype mapping (CustomerCreated → Customer, InvoiceGenerated → Sales Invoice, etc.)
- ✅ Test suite with monkeypatch mocking (test_push_day11.py)
- ✅ Platform_id custom field for exactly-once semantics via idempotency

**Remaining for Day 11:**
- Fix AdapterEventType enum mapping (customer_upserted pattern)
- Run full pytest suite (4/5 tests pending fixes)
- Integrate push handler into app startup lifecycle
- Document ERP API contract expectations

**Exit Criteria:**
- Duplicate event creates one external-ERP record ✓ (test structure ready)
- Ledger entries record both success and failure ✓
- Retry mechanism defined in Day 12

---

### Day 12: Adapter Mappings & Retry Policy
**Objective:** Full Customer/Invoice/Payment mappings, retry policy, DLQ

**Must-Do:**
1. **Entity Mappings:**
   - Customer: name, email, billing address, tax ID
   - Sales Invoice: customer, line items, invoice_date, due_date, amount
   - Payment Entry: amount_received, invoice_reference, payment_date, mode_of_payment

2. **Retry Logic:**
   - Max 5 attempts with exponential backoff (1s, 2s, 4s, 8s, 16s)
   - Update `AdapterLedgerEntry.attempts` and `last_error` on each retry
   - Failed event to DLQ after 5 retries

3. **DLQ Implementation:**
   - Separate `dead_letter_events` topic in Dapr pubsub config
   - Hook: if status = FAILED and attempts >= 5, publish to DLQ
   - Manual repair workflow: fix in external ERP, re-publish from DLQ

4. **Tests:**
   - Test idempotent replay with 3 duplicate events
   - Test poison message (unmappable event) goes to DLQ
   - Test 5-attempt retry with exponential backoff

---

### Day 13: Reconciliation Job
**Objective:** Scan external ERP for discrepancies, fix missing records, replay DLQ

**Must-Do:**
1. **As Container Apps Job:**
   - Schedule: 15-minute incremental scan + nightly full pass
   - Terraform: add Job resource in Container Apps environment

2. **Incremental Scan (15 min):**
   - Query external ERP modified_at > last_scan_time
   - For each modified record, check platform_id in ledger
   - If in ledger but external mismatch → update ledger
   - If in ledger as FAILED → attempt re-post

3. **Nightly Full Scan:**
   - Query all external records (per tenant)
   - Verify each has ledger entry
   - Repair missing ledger entries

4. **DLQ Replay:**
   - After reconciliation fixes, auto-replay DLQ
   - Max 2 re-attempts before manual intervention

5. **Tests:**
   - Stop external ERP, verify job detects missing record, re-posts on restart
   - Simulate stale ledger entry, verify reconciliation repairs it

---

### Day 14: Full Pipeline Deploy & Smoke Tests
**Objective:** Deploy all 11 services + adapter + reconciliation job, run smoke tests

**Must-Do:**
1. **Deploy Job:**
   - terraform apply deploys reconciliation Container Apps Job
   - erp_adapter container deployed to Container Apps

2. **Smoke Tests:**
   - Create Property in Dev → verify in external ERP via adapter
   - Create Customer → verify in external ERP with custom_platform_id
   - Create Invoice → verify in external ERP with linked customer
   - Record Payment → verify in external ERP

3. **Failure Drill:**
   - Stop external ERP for 30 minutes
   - Verify outbox queue builds up (awaiting DLQ)
   - Restart external ERP
   - Verify reconciliation job picks up and re-posts all queued events
   - Assert all events posted exactly once (no duplicates)

4. **Monitoring:**
   - Alert rule: DLQ depth > 0 for 30 min
   - Alert rule: Reconciliation job failure
   - Dashboard: ledger entry counts by status

---

### Day 15: Documentation & Days 16-25 Backlog
**Objective:** Polish, document, define frontend work

**Must-Do:**
1. **Service Documentation:**
   - Update each service README: schema, APIs, deployment, runbook
   - Architecture docs: data flow, tenant isolation, error handling
   - Deployment docs: Terraform, secrets, monitoring

2. **Design Doc Review:**
   - Close § 10 (external ERP) open items
   - Document ERP API contract (endpoint patterns, auth, error codes)
   - Record lessons learned

3. **Coverage & Security Report:**
   - Run `pytest --cov` across all 11 services
   - Verify each service meets Vol 5 § 18 targets
   - Publish coverage report
   - Verify CodeQL green on main

4. **Days 16-25 Backlog (to be written):**
   - Lease business logic (rent increment, invoice schedule)
   - Next.js frontend scaffold with Playwright harness
   - Frontend routing, state management, API clients
   - OAuth provider flow on frontend
   - Property CRUD, Lease CRUD, Payment UI
   - Real user journeys (login, create property, lease payment flow)

---

## Frontend Implementation: Days 16+ (Post-Day 15)

### Phase 1: Foundation (Days 16-17)
#### 1.1 Next.js Project Structure
```
frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   ├── signup/
│   │   └── oauth-callback/[provider]/
│   ├── (protected)/
│   │   ├── dashboard/
│   │   ├── properties/
│   │   │   ├── page.tsx (list)
│   │   │   └── [id]/page.tsx (detail)
│   │   └── leases/
│   ├── layout.tsx
│   └── page.tsx (public home)
├── components/
│   ├── Auth/
│   ├── Property/
│   ├── Lease/
│   └── Common/
├── lib/
│   ├── api-client.ts (HTTP wrapper)
│   ├── auth.ts (JWT + OAuth flows)
│   └── types.ts (TS interfaces)
├── e2e/ (Playwright tests)
├── .env.local
└── package.json
```

#### 1.2 Tech Stack
- **Framework:** Next.js 15 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS + ShadCN components
- **State:** React Context (or Zustand for complexity)
- **Auth:** NextAuth.js v5 (supports OAuth + custom JWT)
- **Testing:** Playwright (E2E), Jest + Testing Library (unit)
- **API:** Fetch API + React Query for data fetching

#### 1.3 Environment & Deployment
- Local: `npm run dev` (Next.js dev server at :3000)
- CI: `next build && next start` (production-like)
- Docker: Multi-stage, Node 20-alpine
- Docker Compose: Integrates with backend stack for local dev

### Phase 2: Authentication (Days 17-18)

#### 2.1 OAuth Flows (Microsoft Entra, Google, Apple)
- NextAuth.js providers for each OAuth provider
- Callback → backend POST /api/v1/auth/{provider}
- Backend returns JWT
- Frontend stores JWT in httpOnly cookie

#### 2.2 Local Account
- Login form: email + password
- Backend POST /api/v1/auth/local
- Password hashing: bcrypt (backend only)
- JWT issued on successful auth

#### 2.3 JWT Validation & Tenant Context
- JWT decoded: extract `tenantId`, `userId`, `role`
- Middleware: verify JWT on protected routes
- Context: inject tenant ID into API client headers
- Auto-redirect to login on JWT expiry

### Phase 3: Core UI (Days 19-21)

#### 3.1 Dashboard (authenticated home)
- Summary: property count, lease count, revenue this month
- Quick actions: Create Property, View Leases, Payments
- Recent activity feed

#### 3.2 Property Management
- **List View:** Properties by tenant, filter by type (residence/commercial/RV)
- **Create Form:** Property details, address, unit configuration
- **Detail View:** Property + buildings + units tree view
- **Edit:** Update property metadata
- **Delete:** Soft-delete with audit trail

#### 3.3 Lease Management (MVP)
- **List View:** Active leases per property
- **Create Form:** Tenant, unit, move-in date, rent amount, increment rate
- **Detail View:** Lease summary, linked payments
- **Actions:** Renew, terminate (mark end_date)

#### 3.4 Payment/Invoicing (MVP)
- **List View:** Pending, paid, overdue invoices
- **Create/Post:** Manual payment entry (payment date, amount, mode)
- **Link:** Auto-link to invoice via external ERP reference
- **Status:** Pending → Posted (synced to ERP) → Reconciled

### Phase 4: Cross-Cutting Concerns (Days 22-23)

#### 4.1 Error Handling
- Network error: retry + user-friendly message
- 401 Unauthorized: redirect to login
- 403 Forbidden: show "Access Denied" page
- 422/500: show error details + support contact

#### 4.2 Loading States & Optimistic Updates
- Skeleton loaders while fetching
- Optimistic UI updates (immediate, revert on error)
- Progress indicators for long operations

#### 4.3 Responsive Design
- Mobile: 1-column layout, hamburger nav
- Tablet: 2-column, side panel
- Desktop: 3+ column, full controls
- Touch-friendly: larger buttons, no hover-only features

#### 4.4 Accessibility
- ARIA labels, semantic HTML
- Keyboard navigation (Tab, Enter, Escape)
- Color contrast (WCAG AA)
- Screen reader testing with NVDA/JAWS

### Phase 5: Testing & Quality (Days 23-24)

#### 5.1 Playwright E2E Tests (in `.github/workflows/e2e.yml`)
Test journeys:
1. **Auth Flow:** Login via Entra → see dashboard
2. **OAuth Flow:** Login via Google → auto-redirect to tenant context
3. **Property Flow:** Create property → view in list → edit → delete
4. **Lease Flow:** Create lease → verify in external ERP
5. **Payment Flow:** Record payment → verify posted to ERP → reconciled

#### 5.2 Unit & Integration Tests
- API client mocking (MSW - Mock Service Worker)
- Component tests: form inputs, error messages, loading states
- Hook tests: auth context, API queries
- Target: 80% coverage on components, 90% on utilities

#### 5.3 Bundle Size & Performance
- Lighthouse CI: Performance 90+, Accessibility 95+
- Bundle: < 200KB (gzipped)
- Lighthouse CLS < 0.1, LCP < 2.5s

### Phase 6: Mobile Apps (Days 25+)

#### 6.1 React Native / Expo Setup
```
mobile/
├── app/
│   ├── (auth)/
│   ├── (tabs)/
│   │   ├── home/
│   │   ├── properties/
│   │   └── leases/
│   └── layout.tsx (native navigation)
├── components/
├── lib/
├── e2e/ (Detox for native E2E)
└── eas.json (EAS Build config)
```

#### 6.2 Android App
- Build: EAS Build (managed service by Expo)
- Deployment: Google Play Store
- Minimum SDK: Android 13 (API 33)
- Features: Push notifications (Firebase), offline-first

#### 6.3 iOS App
- Build: EAS Build + TestFlight for beta
- Deployment: Apple App Store
- Minimum: iOS 14
- Features: Push, biometric login, home screen shortcuts

#### 6.4 Shared Code
- Core auth, API client, types in `packages/` (monorepo)
- Web: Next.js wraps shared code
- Mobile: Expo wraps shared code
- Test & build once, deploy to 3 platforms

---

## Frontend CI/CD Integration

### GitHub Actions: e2e.yml
```yaml
name: E2E Tests
on: [pull_request, push to main/develop]

jobs:
  test:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: cd frontend && npm ci
      
      - name: Build frontend
        run: cd frontend && npm run build
      
      - name: Bring up backend + ERP
        run: docker compose up -d
      
      - name: Wait for services
        run: npm run test:health
      
      - name: Run Playwright tests
        run: cd frontend && npx playwright test
      
      - name: Upload artifacts
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: frontend/playwright-report/
      
      - name: Report results
        run: npm run test:summarize
```

---

## Success Criteria for Days 11-15+26

### Backend (Days 11-15)
- ✓ ERP adapter push/retry/DLQ fully operational
- ✓ Full pipeline green (build → test → deploy)
- ✓ All 11 services meet coverage targets
- ✓ Smoke tests pass with zero duplicates in ERP

### Frontend (Days 16-25)
- ✓ Responsive web app (desktop, tablet, mobile browsers)
- ✓ All 4 OAuth providers work (Entra, Google, Apple, local)
- ✓ Property/Lease/Payment CRUD operational
- ✓ E2E tests cover 5 critical journeys
- ✓ Accessibility: WCAG AA compliant

### Mobile (Days 26+)
- ✓ iOS app on App Store
- ✓ Android app on Google Play
- ✓ Feature parity with web (auth, property, lease, payment)
- ✓ Push notifications, offline-first sync

---

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| ERP API surprises | Day 7 spike documented all edge cases; hardened error handling |
| Frontend complexity | Scaffold from ShadCN templates; use shared monorepo patterns |
| Mobile dev environment setup | Use EAS Build (managed) rather than local Xcode/Android Studio |
| Cross-platform state sync | React Query + API Client layer abstracts backend; same code on web/mobile |
| OAuth provider onboarding | Parallelize: dev Entra in Days 17-18, Google in 18-19, Apple in 19-20 |
| TypeScript learning curve | Strict tsconfig; LSP integration in IDE; avoid `any` |

