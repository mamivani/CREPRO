# CREPRO

Unified Property Operations Platform. Architecture, design and delivery plan for a multi-tenant property management SaaS that uses ERPNext as its financial system of record.

## Layout

| Path | Contents |
|---|---|
| [docs/architecture](docs/architecture) | Architecture spec (PDF, Volumes 1–6) |
| [docs/adr](docs/adr) | Architecture decision records |
| [docs/design](docs/design) | Component designs, including the [ERP Adapter hybrid sync design](docs/design/erp-adapter-hybrid.md) |
| [docs/plan](docs/plan) | Delivery plans, including the [15-day solo plan](docs/plan/15-day-plan-solo.md) |
| [packages/crepro-common](packages/crepro-common) | Shared library: settings, tenant context, event envelope, app factory |
| [services](services) | One FastAPI service per bounded context (see below) |
| [.github/workflows](.github/workflows) | CI: ruff lint and pytest for every package |
| `vendor/erpnext` | Local, untracked copy of the upstream financial system (reference only, not part of the repo) |
| `sample_code/` | Local, untracked reference code used for analysis (not part of the repo) |

## Services

| Service | Package | Responsibility |
|---|---|---|
| identity | `crepro-identity` | Users, roles, SSO federation |
| tenant | `crepro-tenant` | Tenant onboarding, tier assignment, isolation metadata |
| property | `crepro-property` | Portfolio, buildings, units, amenities |
| lease | `crepro-lease` | Lease lifecycle, rent schedules, renewals |
| reservation | `crepro-reservation` | Short-stay bookings, availability, calendars |
| payment | `crepro-payment` | Payment intents, processor webhooks, receipts |
| document | `crepro-document` | Documents, retention, audit trail |
| utility | `crepro-utility` | Meters, readings, utility billing |
| maintenance | `crepro-maintenance` | Work orders, inspections, vendor dispatch |
| reporting | `crepro-reporting` | KPIs and read models |
| erp_adapter | `crepro-erp-adapter` | The only service that talks to the external financial system |

Each service exposes `GET /health` and has a `tests/` folder. Business logic is not implemented yet.

## Getting started

```powershell
docker compose up -d                      # PostgreSQL 16 and Redis 7
python -m venv .venv
.\.venv\Scripts\python -m pip install -e packages\crepro-common[dev]
foreach ($s in Get-ChildItem services -Directory) { .\.venv\Scripts\python -m pip install -e "services\$($s.Name)[dev]" }
.\.venv\Scripts\python -m pytest packages\crepro-common\tests
.\.venv\Scripts\ruff check .
```

Backend stack: [ADR-014](docs/adr/ADR-014-backend-stack.md) (Python 3.12+, FastAPI).

## Status

Planning and design are done. The base code structure is in place: one package per service, shared library, CI, and local infrastructure. Next steps are the frontend (Next.js, ADR-003), Terraform, and domain logic, following the [15-day plan](docs/plan/15-day-plan-solo.md).
