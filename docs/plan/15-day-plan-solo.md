# 15-Day Implementation Plan (Solo)

**Team:** 1 person (full-stack, DevOps and QA combined). **Duration:** 15 working days.
**Basis:** [Architecture spec](../architecture/Complete%20Property%20Management%20Software%20Architecture%20Specifications.pdf), [ADR-013](../adr/ADR-013-message-broker.md), [ERP Adapter design](../design/erp-adapter-hybrid.md).

## Scope

**In:**
- Repo, CI, and Terraform for Dev (Vol 4)
- Identity: local login and JWT with `tenantId`, `userId`, `role` claims (Entra ID wired but not required to pass)
- Property Service: Create Property with tenant isolation and audit (Vol 6 §6)
- ERP Adapter (hybrid): outbox, Service Bus push, scheduled reconciliation
- ERPNext v15 running locally and in Dev, with Customer, Sales Invoice and Payment Entry posting

**Out (moved to Days 16–25 or later sprints):**
- Lease, Applicant, Resident, and the lease document flow
- Live Stripe and ACH (Payment Entry is posted from a test payment event)
- Reservations, reporting dashboards, maintenance, utility billing, white label, AI

## Daily plan

| Day | Work | Done when |
|---|---|---|
| 1 | Create private `CREPRO` repo; commit ERPNext copy (`vendor/erpnext`), spec, ADR-013, design doc, this plan. Set up branch protection and PR template. | Repo on GitHub, private, pushed |
| 2 | GitHub Actions CI (lint, unit tests, CodeQL, Dependabot). Choose the service language and framework and record it in an ADR. | CI green on a skeleton service |
| 3 | Terraform for Dev: resource group, Key Vault, PostgreSQL Flexible Server (private), Storage, Container Apps environment, Service Bus Standard namespace with `erp-events` topic. Remote state in Azure Storage. | `terraform apply` through the pipeline only |
| 4 | Local single-command startup (docker compose): PostgreSQL, Dapr sidecar with in-memory pub/sub, ERPNext v15 via frappe_docker. | `make up` gives a working local stack |
| 5 | Identity: local login, JWT issuing and validation, tenant resolution (custom domain > subdomain > claim). Health and OpenTelemetry basics. | Authenticated request reaches a service with tenant context |
| 6 | ERPNext spike: create API key on a test site and verify the token header against `frappe/auth.py`. Create Customer and Sales Invoice through `/api/resource`. Record results in design doc §10. | Invoice created via API; open items resolved or noted |
| 7 | Property Service schema: `property`, `building`, `unit`, `rv_site` with `tenant_id` on every row. Migrations. Audit table. | Migrations apply cleanly in Dev |
| 8 | Create Property API (`/api/v1/properties`), RBAC checks, audit event on write. | Story "Create Property" passes manual checks |
| 9 | Cross-tenant isolation tests for Property (tenant A cannot read or write tenant B). Coverage for domain and API logic. | Isolation tests in CI, domain and API coverage at target (80%) |
| 10 | Outbox table in Property and adapter databases. Outbox relay publishing via Dapr to `erp-events`. | Event published in the same transaction as the write |
| 11 | ERP Adapter push path: subscribe to `erp-events` with session key `tenantId:entityId`. Adapter ledger. Idempotency via `platform_id` custom field in ERPNext. | Duplicate event creates one ERPNext record |
| 12 | Adapter mappings: Customer, Sales Invoice, Payment Entry (linked to invoice). Retry policy (5 attempts, back-off) and dead-letter queue. | Paid invoice produces matching Payment Entry; a poison message lands in DLQ |
| 13 | Reconciliation job: 15-minute incremental scan and nightly full pass. Re-posts missing records and replays DLQ after fixes. | Deleting an ERPNext record is repaired by the next run |
| 14 | Deploy adapter, Property, Identity, and ERPNext to Dev Container Apps through GitHub Actions. Smoke tests. Alert rules for DLQ and failed jobs. Failure drill: stop ERPNext for 30 minutes, restart, confirm events post. | Smoke tests pass; drill passes with no manual step |
| 15 | Demo. Update README and runbook. Review open items in design doc. Write Days 16–25 backlog (Lease slice first). | Demo done; backlog written; design doc §10 closed or tracked |

## Exit criteria (end of Day 15)

- A property created in Dev is visible only to its tenant, and the write is audited.
- An invoice and payment created on the platform appear in ERPNext exactly once, including after a retry.
- A dead-lettered event is found by reconciliation and replayed after repair.
- The stack starts with one command locally and deploys to Dev through the pipeline.

## Risks for a one-person team

| Risk | Mitigation |
|---|---|
| Scope creep into Lease or Stripe | Hold to the Out list. Anything new goes to the Day 15 backlog. |
| ERPNext API surprises (auth, custom fields) | Day 6 spike is timeboxed. If it slips, Customer posting moves ahead and Payment Entry moves to Day 16. |
| Tenant isolation mistakes | Isolation tests are written on Day 9, before the adapter reads any data. |
| No second reviewer | Use CodeQL, Dependabot, and the isolation test suite as automated gates. Self-review every PR against the checklist in Vol 5 §7. |

## Budget impact

- Azure Service Bus Standard: about $10/month base (ADR-013).
- Dev Container Apps, PostgreSQL, Key Vault and Storage: within the spec's Dev budget. Stop non-prod resources outside working hours to keep cost down.
