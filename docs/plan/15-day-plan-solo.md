# 15-Day Implementation Plan (Solo) - REVISED 3

**Team:** 1 person (full-stack, DevOps and QA combined). **Duration:** 15 working days.
**Basis:** [Architecture spec](../architecture/Complete%20Property%20Management%20Software%20Architecture%20Specifications.pdf) (Vol 1 §6, §9, §11; Vol 3; Vol 4; Vol 5, including its internal ADR-009 Terraform and ADR-010 GitHub/CodeQL decisions), [ADR-013](../adr/ADR-013-message-broker.md), [ADR-014](../adr/ADR-014-backend-stack.md), [ERP Integration design](../design/erp-adapter-hybrid.md).

**Revision 3.** Major architectural shift: CommonERP (ERPNext v15.124.3) is now **integrated as a core CREPRO service**, not an external system. CREPRO becomes a unified multi-tenant platform combining property management + embedded ERP, eliminating the adapter pattern and simplifying the architecture. All CommonERP capabilities (General Ledger, AR/AP, Sales, Purchases, Accounting) are now native to CREPRO, deployed as a containerized service alongside Identity, Property, and other domains. Multi-tenancy is enforced at the Common ERP service level via tenant routing and company isolation.

**Key Changes from Revision 2:**
- CommonERP moved from external service to core service (hosted in this repo under `services/common_erp/`)
- Vendor ERPNext at `vendor/erpnext/` with multi-tenant customizations
- Adapter pattern simplified: direct service-to-service posting, no message broker for ERP (keeping internal outbox/events for Property→ other domains)
- Single container orchestration: all services deploy together (Identity, Property, CommonERP, Lease, Payment, etc.)
- Terraform provisions CommonERP database and site alongside other services
- No external ERP API calls; all data flows internal through Dapr and direct service boundaries

## Scope

**In:**
- Repo, branch protection, PR template, and branching strategy (`main`/`develop`, `feature/`, `bugfix/`, `hotfix/`, `release/`) (Vol 5 §6–§7)
- **CI/CD**: five GitHub Actions workflows — `build`, `test`, `security`, `terraform`, `deploy` — implementing the pipeline Push → Build → Unit Tests → Security Scan → Terraform Plan → Approval Gate → Terraform Apply → Deploy Containers → Smoke Tests (Vol 4 §16, Vol 5 §15)
- **Code quality and security scanning**: ruff lint, CodeQL, Dependabot, secret scanning, and container image scanning, all required and merge-blocking (Vol 5 §16–§17, spec ADR-010)
- **Containerization**: every service packaged as an OCI-compliant Docker image (Vol 1 §9.3), including CommonERP, a shared `docker-compose.yml` for local dev (Postgres, Redis, Dapr sidecars, CommonERP service), and image build/push to Azure Container Registry in CI
- **Terraform for Dev on Azure** (Vol 4): resource group, Key Vault, PostgreSQL Flexible Server (private) with CommonERP database + site provisioning, Storage, Container Registry, Container Apps environment with one Container App per service (including CommonERP), internal Service Bus for domain events (outbox relay, property→lease→payment flows, NOT for ERP). Remote state in Azure Storage; no portal-created infrastructure (spec ADR-009)
- **Identity**: OAuth2/OIDC login via Microsoft Entra ID (preferred enterprise provider), Google OAuth, and Apple Sign-In, plus a Local Account fallback (Vol 1 §6.2–§6.4); endpoints `POST /api/v1/auth/{microsoft,google,apple}` and `POST /api/v1/auth/refresh` (Vol 3); JWT issuing with `tenantId`, `userId`, `role` claims; tenant resolution (custom domain > subdomain > claim)
- **CommonERP (ERPNext v15.124.3)**: Integrated as a core CREPRO service, not external. Vendored at `vendor/erpnext/` with multi-tenant customizations. Handles General Ledger, AR/AP, Sales, Purchases, Accounting for all 11 services. Multi-tenancy via: one Frappe site with one Company per tenant (shared tier) or one site per tenant (dedicated tier). Routing layer ensures Property service, Payment service, Lease service post to their tenant's CommonERP Company. No external API calls; internal service-to-service HTTP or direct database access.
- **Comprehensive testing for every module**: unit, integration, and contract tests (OpenAPI-based) for all 11 services plus `crepro-common`, hitting the Volume 5 §18 coverage targets (table below). CommonERP tests verify multi-tenant document creation (Customer, Sales Invoice, Payment Entry) and cross-tenant isolation.
- **Property Service**: Create Property with tenant isolation and audit (Vol 6 §6)
- **Events and Outbox**: Property/Lease/Payment services publish domain events (PropertyCreated, LeaseExecuted, PaymentPosted) via Dapr pub/sub to Service Bus topics. Internal domains subscribe (e.g., Payment service subscribes to LeaseExecuted to trigger invoice generation). CommonERP is a subscriber to critical events, posting GL entries synchronously when events fire.

**Out (moved to Days 16–25 or later sprints):**
- Full business-logic depth for Lease (increment engine, invoice-schedule generation), Reservation, Maintenance dispatch, utility billing, reporting dashboards, white label, AI
- Live Stripe and ACH (Payment Entry is posted from a test payment event)
- Staging/Production environments and multi-region DR (Dev only this phase)
- Per-tenant dedicated infrastructure provisioning (Vol 4 §14–§15)
- CommonERP advanced modules (Projects, Manufacturing, HR, CRM) — only core accounting used in this phase

## Daily plan

| Day | Work | Done when |
|---|---|---|
| 1 | Create private `CREPRO` repo; commit spec, ADRs, design doc, this plan. Branch protection on `main`/`develop`, PR template with Purpose/Changes/Testing/Security Impact/Database Impact/Rollback Strategy sections (Vol 5 §7). Stub the five workflow files (`build.yml`, `test.yml`, `security.yml`, `terraform.yml`, `deploy.yml`). | Repo on GitHub, private, pushed; all five workflows run (even as no-ops) on a PR |
| 2 | Dockerize: one multi-stage, OCI-compliant Dockerfile per service plus `crepro-common` and CommonERP (Vol 1 §9.3), and a shared `docker-compose.yml` (Postgres, Redis, Dapr sidecars, CommonERP service with site provisioning). `build.yml` builds every image in a matrix. | `docker compose up` gives a working local stack with CommonERP available at http://localhost:8080; `build.yml` is green on all images |
| 3 | Terraform for Dev: resource group, Key Vault, PostgreSQL Flexible Server (private) with CommonERP database provisioning, Storage, Container Registry, Container Apps environment (with CommonERP Container App), Service Bus Standard namespace with domain-event topics. Remote state in Azure Storage. `terraform.yml` runs plan on PR, apply only on `main` after approval. | `terraform apply` provisions CommonERP site and database; CommonERP is reachable from other Container Apps through private DNS |
| 4 | Harden `test.yml` (pytest + coverage gate per service, including CommonERP multi-tenant verification) and `security.yml`: CodeQL, Dependabot config, secret scanning, Trivy container scan on built images. Wire the DevSecOps gate: merge blocked on critical vulnerability, failed test, failed build, or failed security scan (Vol 5 §16–§17). | A PR with a seeded critical vulnerability or a failing test is blocked from merge |
| 5 | Identity: OAuth2/OIDC against Microsoft Entra ID, Google, and Apple, plus Local Account fallback (Vol 1 §6.2). Endpoints `/api/v1/auth/{microsoft,google,apple,refresh}` (Vol 3). JWT issuing/validation with `tenantId`/`userId`/`role` claims; tenant resolution (custom domain > subdomain > claim). Health and OpenTelemetry basics. | All four login paths (3 OAuth + local) each return a valid JWT with tenant context in Dev |
| 6 | Comprehensive tests for Identity and `crepro-common`: unit tests for token exchange and JWT validation (mocked IdP responses per provider), integration tests for each login endpoint, contract tests against the OpenAPI spec. | Coverage targets met for this slice (table below); contract tests pass in CI |
| 7 | CommonERP spike: Vendor ERPNext v15.124.3 under `vendor/erpnext/`, identify multi-tenant customization points (routing, Company assignment, tenant filtering on reads). Create a Python spike script to verify: API key creation, HTTP Basic Auth, Customer + Sales Invoice posting via `/api/resource`, multi-tenant isolation (Tenant A's invoices in Company A, Tenant B's in Company B). Update design doc with integration architecture. | CommonERP API key created; Customers and invoices posted; isolation verified; design doc (erp-integration-design.md) documents multi-tenant routing strategy |
| 8 | Property Service schema (`property`, `building`, `unit`, `rv_site`, `tenant_id` on every row), migrations, audit table, Create Property API (`/api/v1/properties`) with RBAC and an audit event on write. When Property is created, publish PropertyCreated event to event topics. Deploy via the Day 3 Terraform + Day 2 container image. | Story "Create Property" passes manual checks in Dev; event published to Service Bus |
| 9 | Comprehensive tests, pass 1 — Property: unit (domain), integration (API + DB), cross-tenant isolation (tenant A cannot read or write tenant B), contract tests. Pass 2 — backfill the same test shape (unit/integration/contract, coverage targets) onto the other nine already-scaffolded services (tenant, lease, reservation, payment, document, utility, maintenance, reporting, common_erp_service). CommonERP tests focus on: multi-tenant Company isolation, GL entry posting for events from Property/Lease/Payment services. | Isolation tests in CI for all services; CommonERP posts GL entry to correct Company; every service meets its Volume 5 §18 coverage target |
| 10 | Outbox table in Property and Lease databases. Outbox relay publishing via Dapr to Service Bus topics (property-events, lease-events, payment-events, etc.). Unit/integration tests: write and outbox row commit in one transaction; relay delivers at-least-once. | Event published in the same transaction as the write; tests green |
| 11 | Event subscribers: Property service publishes PropertyCreated; CommonERP service (via HTTP POST to /api/resource) creates Customer when PropertyCreated fires. Lease service listens to PropertyCreated to set up available units. Payment service listens to LeaseExecuted to trigger invoice generation. Idempotency via event id + payload hash deduplication at subscriber level. | PropertyCreated event triggers Customer creation in CommonERP Company; tests verify idempotent re-delivery |
| 12 | CommonERP GL posting: When Payment service posts PaymentPosted event, CommonERP creates Payment Entry linked to Sales Invoice (same tenant's Company). GL postings. Retry policy (5 attempts, back-off) on event processing. Tests: idempotent replay, poison message handling. | Paid invoice produces matching GL entry in CommonERP; duplicate event creates one Payment Entry |
| 13 | Reconciliation: Nightly full pass compares Property/Lease/Payment records with CommonERP (by platform_id field). Re-posts missing GL entries and re-creates missing CommonERP documents. Container Apps Job defined in Terraform, every 15 minutes (incremental), nightly (full). | Deleting a CommonERP record is repaired by the next reconciliation run; cross-tenant audit confirms no leakage |
| 14 | `deploy.yml` deploys every service (Identity, Property, CommonERP, Lease, Payment, Tenant, Document, Utility, Maintenance, Reporting, Reconciliation Job) to Dev Container Apps through the full pipeline. Smoke tests. Alert rules for failed event processing and reconciliation jobs. Failure drill: stop CommonERP for 30 minutes, restart, confirm events post and GL entries appear. | Full pipeline green end to end; smoke tests pass; drill passes with no manual step; CommonERP GL complete after restart |
| 15 | Demo. Update each service's `README.md`/`architecture.md`/`deployment.md`/`runbook.md` (Vol 5 §20). Close erp-integration-design.md with CommonERP architecture finalized. Publish the coverage and security-scan summary. Write Days 16–25 backlog (Lease business logic, reconciliation enhancements, Stripe integration, reporting). | Demo done; all services deployed and tested; backlog written; design docs finalized; CommonERP GL verified across all tenant Companies |

## Testing strategy and coverage targets

Test pyramid per Vol 5 §18: unit tests (domain logic, no I/O), integration tests (API + database), contract tests (OpenAPI schema and consumer-contract checks between services), system tests (the Day 14 smoke tests and Day 14 failure drill). Every service publishes its OpenAPI contract (Vol 5 §19).

| Area | Coverage target |
|---|---|
| Domain logic | 90% |
| APIs | 80% |
| Utilities | 90% |
| Critical workflows (auth, tenant isolation, ERP posting, reconciliation) | 95% |

`test.yml` fails the build below target for any changed package; a report of current coverage per service is published on Day 15.

## Code quality and security scanning

Mandatory, merge-blocking scans (Vol 5 §16–§17, spec ADR-010):

| Check | Tool | Gate |
|---|---|---|
| Lint / type-correctness | ruff (existing), extend with mypy if a service takes on non-trivial typing | Fails `build.yml` |
| Static analysis (SAST) | CodeQL | Required check on every PR |
| Dependency vulnerabilities | Dependabot (alerts + auto PRs) | Required check; critical finding blocks merge |
| Secret scanning | GitHub secret scanning + push protection | Required check |
| Container image scanning | Trivy against every built image | Required check in `security.yml`; critical CVE blocks merge |

PR required checks mirror Vol 5 §7: Build Success, Tests Pass, CodeQL Pass, Dependency Scan Pass, Lint Pass, Architecture Review.

## Exit criteria (end of Day 15)

- A user can sign in through Microsoft Entra ID, Google, Apple, or a local account, and each path returns a JWT with tenant context.
- A property created in Dev is visible only to its tenant, and the write is audited.
- An invoice and payment created on the platform are posted to CommonERP (same Company/tenant) exactly once, including after a retry, visible in CommonERP GL/AR/AP.
- A property creation event triggers CommonERP GL entry posting (via event subscriber) in the correct tenant's Company.
- Every one of the 11 services plus CommonERP is containerized, deployed to Dev through Terraform and the GitHub Actions pipeline, and meets its Volume 5 §18 coverage target.
- CommonERP multi-tenancy is verified: Tenant A's invoices are in Company A, Tenant B's invoices are in Company B, no cross-tenant data leakage.
- CodeQL, Dependabot, secret scanning, and container scanning are all green (or have tracked, non-critical findings) on `main`.
- The stack starts with one command locally (`docker compose up`, including CommonERP site provisioning) and deploys to Dev through the pipeline only.

## Risks for a one-person team

| Risk | Mitigation |
|---|---|
| Scope creep into Lease business logic, full ERP module suite, or Stripe | Hold to the Out list (core accounting only, no HR/Projects/Manufacturing). Anything new goes to the Day 15 backlog. |
| CommonERP vendoring and multi-tenant customization takes longer than Day 7 spike allows | Day 7 spike is timeboxed (4 hours). If vendor/customization slips, move CommonERP integration to Day 16 and backfill ERP Adapter pattern from Revision 2 for Days 8-15 exit. |
| Three OAuth providers (Entra, Google, Apple) each have different app-registration and callback setup | Timebox Day 5 per provider; if Apple Sign-In's developer-account step slips, ship Entra + Google + Local first and track Apple as a Day 16 follow-up. |
| Comprehensive testing across 11 services + CommonERP in the time available | Day 9 scope is explicitly the existing CRUD surface, not full domain logic; reuse the shared `build_crud_router`/`InMemoryRepository` test patterns. CommonERP tests focus on multi-tenant isolation and GL posting, not all doctype CRUD. |
| CommonERP customizations break between upgrades or have security holes | Use official v15.124.3 image; minimal custom hooks (just tenant routing and Company assignment). Spike validates API before customization. |
| Tenant isolation mistakes in CommonERP routing | Isolation tests written on Day 9 include CommonERP posting verification; Property→CommonERP event flow tests confirm correct Company posting. |
| No second reviewer | Use CodeQL, Dependabot, secret scanning, container scanning, and the isolation test suite as automated gates. Self-review every PR against the checklist in Vol 5 §7. |

## Budget impact

- **Azure Service Bus Standard:** about $10/month base for domain events (Property→Lease→Payment topics) (ADR-013).
- **Azure Container Registry (Basic tier):** for 12 service images (11 CREPRO services + CommonERP): low single-digit $/month.
- **Dev Container Apps:** running all 11 CREPRO services plus CommonERP, PostgreSQL (single Flexible Server with multiple databases), Key Vault, and Storage: higher than Revision 2 due to CommonERP add-on. Within spec budget; stop non-prod resources outside working hours.
- **CommonERP cost:** ERPNext is open-source (MIT license); no Frappe licensing cost. Hosting cost is included in Container Apps allocation.
- **Three OAuth provider registrations:** no direct Azure cost; Apple Sign-In requires active Apple Developer Program membership ($99/year) if not already held.

## Architecture vs. Revision 2

| Aspect | Revision 2 (External ERP) | Revision 3 (Integrated CommonERP) |
|--------|---------------------------|----------------------------------|
| ERP system | External (Frappe/ERPNext) | Integrated (CommonERP, ERPNext v15.124.3 in repo) |
| Deployment | Separate docker-compose profile | Native Container App alongside other services |
| Adapter | ERP Adapter service (Day 11-13) | Event subscribers (Day 11-12) |
| Data flow | Property → Adapter → Service Bus → ERPNext | Property → Outbox → Event subscribers → CommonERP GL |
| Multi-tenancy | One site + N Companies (or N sites) | One CommonERP service + N Companies per tenant |
| Testing scope | Adapter integration tests, external API validation | End-to-end event flow, CommonERP GL verification |
| Database | Separate ERP database | Shared PostgreSQL with CommonERP schema |
| Complexity | Higher (adapter, DLQ, reconciliation, external API) | Lower (direct event handling, internal API) |
| Scope reduction | Days 11-13 focus on adapter + reconciliation | Days 11-12 focus on event-driven GL posting |

