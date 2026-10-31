# 15-Day Implementation Plan (Solo)

**Team:** 1 person (full-stack, DevOps and QA combined). **Duration:** 15 working days.
**Basis:** [Architecture spec](../architecture/Complete%20Property%20Management%20Software%20Architecture%20Specifications.pdf) (Vol 1 §6, §9, §11; Vol 3; Vol 4; Vol 5, including its internal ADR-009 Terraform and ADR-010 GitHub/CodeQL decisions), [ADR-013](../adr/ADR-013-message-broker.md), [ADR-014](../adr/ADR-014-backend-stack.md), [ERP Adapter design](../design/erp-adapter-hybrid.md).

**Revision 2.** Expands Revision 1 to pull forward six engineering disciplines the spec requires platform-wide (Vol 5 §30: every feature needs tests, Terraform, and security review) instead of leaving them for Days 16+: comprehensive per-service testing, multi-provider OAuth, containerization, Terraform-to-Azure, full CI/CD, and code quality/security scanning. The functional backbone (Identity → Property → Outbox → ERP Adapter → Reconciliation → Dev deploy) is unchanged from Revision 1; it is now built container-first, behind CI/CD gates, with every service tested and deployed the same way instead of some services staying manual or untested until later.

## Scope

**In:**
- Repo, branch protection, PR template, and branching strategy (`main`/`develop`, `feature/`, `bugfix/`, `hotfix/`, `release/`) (Vol 5 §6–§7)
- **CI/CD**: five GitHub Actions workflows — `build`, `test`, `security`, `terraform`, `deploy` — implementing the pipeline Push → Build → Unit Tests → Security Scan → Terraform Plan → Approval Gate → Terraform Apply → Deploy Containers → Smoke Tests (Vol 4 §16, Vol 5 §15)
- **Code quality and security scanning**: ruff lint, CodeQL, Dependabot, secret scanning, and container image scanning, all required and merge-blocking (Vol 5 §16–§17, spec ADR-010)
- **Containerization**: every service packaged as an OCI-compliant Docker image (Vol 1 §9.3), a shared `docker-compose.yml` for local dev (Postgres, Redis, Dapr sidecar, external ERP), and image build/push to Azure Container Registry in CI
- **Terraform for Dev on Azure** (Vol 4): resource group, Key Vault, PostgreSQL Flexible Server (private), Storage, Container Registry, Container Apps environment with one Container App per service, Service Bus Standard namespace with `erp-events` topic. Remote state in Azure Storage; no portal-created infrastructure (spec ADR-009)
- **Identity**: OAuth2/OIDC login via Microsoft Entra ID (preferred enterprise provider), Google OAuth, and Apple Sign-In, plus a Local Account fallback (Vol 1 §6.2–§6.4); endpoints `POST /api/v1/auth/{microsoft,google,apple}` and `POST /api/v1/auth/refresh` (Vol 3); JWT issuing with `tenantId`, `userId`, `role` claims; tenant resolution (custom domain > subdomain > claim)
- **Comprehensive testing for every module**: unit, integration, and contract tests (OpenAPI-based) for all 11 services and `crepro-common`, hitting the Volume 5 §18 coverage targets (table below)
- Property Service: Create Property with tenant isolation and audit (Vol 6 §6)
- ERP Adapter (hybrid): outbox, Service Bus push, scheduled reconciliation
- External ERP system running locally and in Dev, with Customer, Sales Invoice and Payment Entry posting

**Out (moved to Days 16–25 or later sprints):**
- Full business-logic depth for Lease (increment engine, invoice-schedule generation), Reservation, Maintenance dispatch, utility billing, reporting dashboards, white label, AI — these services exist, are containerized, tested at the CRUD level, and deployed, but their domain workflows are not built yet
- Live Stripe and ACH (Payment Entry is posted from a test payment event)
- Staging/Production environments and multi-region DR (Dev only this phase)
- Per-tenant dedicated infrastructure provisioning (Vol 4 §14–§15)

## Daily plan

| Day | Work | Done when |
|---|---|---|
| 1 | Create private `CREPRO` repo; commit spec, ADRs, design doc, this plan. Branch protection on `main`/`develop`, PR template with Purpose/Changes/Testing/Security Impact/Database Impact/Rollback Strategy sections (Vol 5 §7). Stub the five workflow files (`build.yml`, `test.yml`, `security.yml`, `terraform.yml`, `deploy.yml`). | Repo on GitHub, private, pushed; all five workflows run (even as no-ops) on a PR |
| 2 | Dockerize: one multi-stage, OCI-compliant Dockerfile per service plus `crepro-common` (Vol 1 §9.3), and a shared `docker-compose.yml` (Postgres, Redis, Dapr sidecar with in-memory pub/sub, external ERP via its official Docker Compose). `build.yml` builds every image in a matrix. | `docker compose up` gives a working local stack; `build.yml` is green on all images |
| 3 | Terraform for Dev: resource group, Key Vault, PostgreSQL Flexible Server (private), Storage, Container Registry, Container Apps environment, Service Bus Standard namespace with `erp-events` topic. Remote state in Azure Storage. `terraform.yml` runs plan on PR, apply only on `main` after approval. | `terraform apply` through the pipeline only; no portal changes (spec ADR-009) |
| 4 | Harden `test.yml` (pytest + coverage gate per service) and `security.yml`: CodeQL, Dependabot config, secret scanning, Trivy container scan on built images. Wire the DevSecOps gate: merge blocked on critical vulnerability, failed test, failed build, or failed security scan (Vol 5 §16–§17). | A PR with a seeded critical vulnerability or a failing test is blocked from merge |
| 5 | Identity: OAuth2/OIDC against Microsoft Entra ID, Google, and Apple, plus Local Account fallback (Vol 1 §6.2). Endpoints `/api/v1/auth/{microsoft,google,apple,refresh}` (Vol 3). JWT issuing/validation with `tenantId`/`userId`/`role` claims; tenant resolution (custom domain > subdomain > claim). Health and OpenTelemetry basics. | All four login paths (3 OAuth + local) each return a valid JWT with tenant context in Dev |
| 6 | Comprehensive tests for Identity and `crepro-common`: unit tests for token exchange and JWT validation (mocked IdP responses per provider), integration tests for each login endpoint, contract tests against the OpenAPI spec. | Coverage targets met for this slice (table below); contract tests pass in CI |
| 7 | External ERP spike: create an API key on a test site, verify the token header, create Customer and Sales Invoice through `/api/resource`. Containerize the external ERP into `docker-compose.yml` and Dev Container Apps. Record results in design doc §10. | Invoice created via API; open items resolved or noted |
| 8 | Property Service schema (`property`, `building`, `unit`, `rv_site`, `tenant_id` on every row), migrations, audit table, Create Property API (`/api/v1/properties`) with RBAC and an audit event on write. Deploy via the Day 3 Terraform + Day 2 container image. | Story "Create Property" passes manual checks in Dev |
| 9 | Comprehensive tests, pass 1 — Property: unit (domain), integration (API + DB), cross-tenant isolation (tenant A cannot read or write tenant B), contract tests. Pass 2 — backfill the same test shape (unit/integration/contract, coverage targets) onto the other nine already-scaffolded services (tenant, lease, reservation, payment, document, utility, maintenance, reporting, erp_adapter). | Isolation tests in CI; every service meets its Volume 5 §18 coverage target |
| 10 | Outbox table in Property and adapter databases. Outbox relay publishing via Dapr to `erp-events`. Unit/integration tests: write and outbox row commit in one transaction; relay delivers at-least-once. | Event published in the same transaction as the write; tests green |
| 11 | ERP Adapter push path: subscribe to `erp-events` with session key `tenantId:entityId`. Adapter ledger. Idempotency via `platform_id` custom field on the external ERP. Container image + Terraform entry for the adapter. | Duplicate event creates one external-ERP record |
| 12 | Adapter mappings: Customer, Sales Invoice, Payment Entry (linked to invoice). Retry policy (5 attempts, back-off) and dead-letter queue. Tests: idempotent replay, poison message to DLQ. | Paid invoice produces matching Payment Entry; a poison message lands in DLQ |
| 13 | Reconciliation job: 15-minute incremental scan and nightly full pass, as a Container Apps Job defined in Terraform. Re-posts missing records and replays DLQ after fixes. | Deleting an external-ERP record is repaired by the next run |
| 14 | `deploy.yml` deploys every service (Identity, Property, ERP Adapter, and the other eight scaffolded services), the reconciliation job, and the external ERP to Dev Container Apps through the full pipeline. Smoke tests. Alert rules for DLQ and failed jobs. Failure drill: stop the external ERP for 30 minutes, restart, confirm events post. | Full pipeline green end to end; smoke tests pass; drill passes with no manual step |
| 15 | Demo. Update each service's `README.md`/`architecture.md`/`deployment.md`/`runbook.md` (Vol 5 §20). Review open items in design doc. Publish the coverage and security-scan summary. Write Days 16–25 backlog (Lease business logic first). | Demo done; backlog written; design doc §10 closed or tracked; docs present for every service |

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
- An invoice and payment created on the platform appear in the external ERP exactly once, including after a retry.
- A dead-lettered event is found by reconciliation and replayed after repair.
- Every one of the 11 services is containerized, deployed to Dev through Terraform and the GitHub Actions pipeline, and meets its Volume 5 §18 coverage target.
- CodeQL, Dependabot, secret scanning, and container scanning are all green (or have tracked, non-critical findings) on `main`.
- The stack starts with one command locally (`docker compose up`) and deploys to Dev through the pipeline only.

## Risks for a one-person team

| Risk | Mitigation |
|---|---|
| Scope creep into Lease business logic or Stripe | Hold to the Out list. Anything new goes to the Day 15 backlog. |
| Three OAuth providers (Entra, Google, Apple) each have different app-registration and callback setup | Timebox Day 5 per provider; if Apple Sign-In's developer-account step slips, ship Entra + Google + Local first and track Apple as a Day 16 follow-up. |
| Comprehensive testing across 11 services in the time available | Day 9 scope is explicitly the existing CRUD surface, not full domain logic (increment engines, invoicing, etc. stay Out); reuse the shared `build_crud_router`/`InMemoryRepository` test patterns across services instead of writing each from scratch. |
| External ERP API surprises (auth, custom fields) | Day 7 spike is timeboxed. If it slips, Customer posting moves ahead and Payment Entry moves to Day 16. |
| Container scanning finds vulnerabilities in base images late in the cycle | Pin and scan base images starting Day 2, not Day 14, so findings surface while there is still runway to patch. |
| Tenant isolation mistakes | Isolation tests are written on Day 9, before the adapter reads any data. |
| No second reviewer | Use CodeQL, Dependabot, secret scanning, container scanning, and the isolation test suite as automated gates. Self-review every PR against the checklist in Vol 5 §7. |

## Budget impact

- Azure Service Bus Standard: about $10/month base (ADR-013).
- Azure Container Registry (Basic tier) for 11+ service images: low single-digit $/month.
- Dev Container Apps (now running all 11 services plus the adapter, reconciliation job, and external ERP), PostgreSQL, Key Vault and Storage: within the spec's Dev budget, but higher than Revision 1's 3-service footprint — stop non-prod resources outside working hours to keep cost down.
- Three OAuth provider registrations (Entra, Google, Apple) have no direct Azure cost; Apple Sign-In requires an active Apple Developer Program membership ($99/year) if not already held.
