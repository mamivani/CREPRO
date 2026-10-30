# CREPRO

Unified Property Operations Platform. Architecture, design and delivery plan for a multi-tenant property management SaaS that uses ERPNext as its financial system of record.

## Layout

| Path | Contents |
|---|---|
| [docs/architecture](docs/architecture) | Architecture spec (PDF, Volumes 1–6) |
| [docs/adr](docs/adr) | Architecture decision records |
| [docs/design](docs/design) | Component designs, including the [ERP Adapter hybrid sync design](docs/design/erp-adapter-hybrid.md) |
| [docs/plan](docs/plan) | Delivery plans, including the [15-day solo plan](docs/plan/15-day-plan-solo.md) |
| [vendor/erpnext](vendor/erpnext) | Local copy of ERPNext v15.124.3 from `frappe/erpnext` (commit `9f33fd5`, GPL-3.0). Not modified. |

## Upstream ERPNext copy

`vendor/erpnext` is a snapshot of the `v15.124.3` tag, taken without its `.git` directory. To update it, re-clone the new tag and replace the folder in a dedicated commit, so changes stay reviewable.

## Status

Planning and design stage. No application code yet.
