# CREPRO

Unified Property Operations Platform. Architecture, design and delivery plan for a multi-tenant property management SaaS that uses ERPNext as its financial system of record.

## Layout

| Path | Contents |
|---|---|
| [docs/architecture](docs/architecture) | Architecture spec (PDF, Volumes 1–6) |
| [docs/adr](docs/adr) | Architecture decision records |
| [docs/design](docs/design) | Component designs, including the [ERP Adapter hybrid sync design](docs/design/erp-adapter-hybrid.md) |
| [docs/plan](docs/plan) | Delivery plans, including the [15-day solo plan](docs/plan/15-day-plan-solo.md) |
| [packages/crepro-common](packages/crepro-common) | Shared library: settings, tenant context, tenant-scoped entity base, in-memory repository, generic CRUD router, event envelope, app factory |
| [services](services) | One FastAPI service per bounded context (see below), each with a multi-stage `Dockerfile` (Vol 1 §9.3) |
| [packages/crepro-common/Dockerfile](packages/crepro-common/Dockerfile) | Builds and tests the shared library in the same image-matrix pattern as every service |
| [dapr/components](dapr/components) | Dapr pub/sub component for local dev (`pubsub.redis`, not `pubsub.in-memory` — see the comment in `pubsub.yaml` for why) |
| [docker-compose.yml](docker-compose.yml) | Local stack: Postgres, Redis, every service with its own Dapr sidecar, and the external ERP behind the `erp` profile |
| [infra/terraform/environments/dev](infra/terraform/environments/dev) | Terraform for the Dev Azure environment: resource group, private VNet-integrated PostgreSQL Flexible Server, Key Vault, Storage, Container Registry, a Container Apps environment (no apps deployed yet — Day 14), and a Service Bus Standard namespace with the `erp-events` topic (ADR-013) |
| [.github/workflows](.github/workflows) | CI/CD: `build`, `test`, `security`, `terraform`, `deploy` (Vol 5 §15). `build` lints and builds every service image in a matrix; `test` runs pytest per package with a 90% coverage gate; `security` runs Semgrep (SAST), gitleaks (secrets), and Trivy (12-image container scan, fails on fixable CRITICAL findings) — substitutes for CodeQL/native secret scanning, which need GitHub Advanced Security, not available on this private repo's plan; `terraform` runs a real `plan` on every PR/push and `apply` on manual dispatch (the Vol 4 §16 approval gate — this repo's plan doesn't support required-reviewer environments, so the gate is a human explicitly triggering the apply after reading the plan); `deploy` is still a Day 1 stub |
| [.github/dependabot.yml](.github/dependabot.yml) | Weekly pip/docker/github-actions dependency updates across every package; vulnerability alerts and automated security fixes enabled |
| `vendor/erpnext` | Local, untracked copy of the upstream financial system (reference only, not part of the repo) |
| `sample_code/` | Local, untracked reference code used for analysis (not part of the repo) |

## Services

| Service | Package | Responsibility |
|---|---|---|
| identity | `crepro-identity` | Users and roles |
| tenant | `crepro-tenant` | Tenant (customer organization) directory: onboarding, tier assignment, isolation metadata |
| property | `crepro-property` | Portfolio, buildings, units, amenities |
| lease | `crepro-lease` | Lease lifecycle, rent schedules, increments, renewals, and resident records |
| reservation | `crepro-reservation` | Short-stay bookings, availability, calendars |
| payment | `crepro-payment` | Payment records, security deposits |
| document | `crepro-document` | Documents, retention, insurance policies |
| utility | `crepro-utility` | Meters, readings, consumption |
| maintenance | `crepro-maintenance` | Work orders, checklists, inventory checkout, outsourced staff |
| reporting | `crepro-reporting` | Report definitions (KPI/read-model catalog) |
| erp_adapter | `crepro-erp-adapter` | The only service that talks to the external financial system; adapter ledger and tenant-to-ERP mapping |

Each service exposes `GET /health` plus a tenant-scoped REST API (`models/`, `schemas/`,
`repository/`, `api/`) built on `crepro_common`'s generic CRUD router and in-memory
repository. Entities were scoped from an analysis of a property-management reference
codebase (doctypes and roles), reshaped into CREPRO's own naming with no copied code,
branding, or URLs. Persistence is in-memory; a real database, auth, and the ERP
push/reconciliation workers are not implemented yet.

## Getting started

```powershell
docker compose up -d                      # Postgres, Redis, all 11 services, one Dapr sidecar each
docker compose --profile erp up -d        # also brings up the external ERP (v15.124.3)
python -m venv .venv
.\.venv\Scripts\python -m pip install -e packages\crepro-common[dev]
foreach ($s in Get-ChildItem services -Directory) { .\.venv\Scripts\python -m pip install -e "services\$($s.Name)[dev]" }
.\.venv\Scripts\python -m pytest packages\crepro-common\tests
.\.venv\Scripts\ruff check .
```

The Python venv setup above is for running tests/lint directly on the host; `docker compose up`
builds and runs every service in its own container, so it works without a local venv too.

Backend stack: [ADR-014](docs/adr/ADR-014-backend-stack.md) (Python 3.12+, FastAPI).

## Dev infrastructure (Azure)

`infra/terraform/environments/dev` provisions the Dev environment. Remote state lives in a
storage account bootstrapped once outside Terraform (`rg-crepro-tfstate`/`creprotfstate` —
the usual chicken-and-egg: Terraform needs a backend before it can manage anything);
`backend.hcl` holds the non-secret account/container/key values. Authentication is Azure AD
(OIDC in CI via a GitHub-federated app registration, `az login` locally) — no stored client
secret anywhere.

```powershell
cd infra/terraform/environments/dev
terraform init "-backend-config=backend.hcl"   # quote the flag on Windows PowerShell 7
terraform plan
```

`terraform apply` only ever runs through `gh workflow run terraform.yml` (or the Actions UI),
never locally and never from a PR — that manual trigger *is* the approval gate between plan and
apply (Vol 4 §16), per ADR-009 (Terraform-only, no portal changes).

## Status

Planning and design are done. Every service has a real tenant-isolated CRUD surface over its
core domain entities (in-memory, pending a database), is containerized (Vol 1 §9.3), and runs
locally with its own Dapr sidecar for pub/sub. The Dev Azure environment is live, provisioned by
Terraform through CI/CD (no portal changes): resource group, private VNet-integrated PostgreSQL
Flexible Server, Key Vault, Storage, Container Registry, a Container Apps environment, and a
Service Bus namespace with the `erp-events` topic. Every PR is gated on lint, a 90% coverage
threshold per package, all 12 images building, and three security scans (Semgrep, gitleaks,
Trivy) — branch protection enforces all of it, including for admins, and merge is blocked on a
failing test or a fixable critical vulnerability (verified directly: seeded both in throwaway
PRs and confirmed GitHub refused to merge even with `--admin`). Next steps are the frontend
(Next.js, ADR-003), wiring real persistence into the services, auth, and the ERP adapter's
push/reconciliation workers, following the [15-day plan](docs/plan/15-day-plan-solo.md).
