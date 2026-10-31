# ADR-014: Backend service stack

- **Status:** Proposed
- **Date:** 2026-10-31
- **Related:** ADR-003 (Next.js frontend), ADR-013 (message broker), [15-day plan](../plan/15-day-plan-solo.md)

## Context

The architecture spec names the services and the Azure platform but leaves the backend language and framework open. The reference codebase used for analysis is Python-based, with domain rules for leases, meters, and rent schedules. A solo developer needs one language across services, fast local feedback, and a small operational footprint.

## Decision

- **Language:** Python 3.12 or newer, using modern typing.
- **Web framework:** FastAPI with Pydantic v2 models and pydantic-settings for configuration.
- **Packaging:** one package per service under `services/`, shared code under `packages/crepro-common`. Each package uses hatchling and declares its own dependencies.
- **Tests and lint:** pytest and ruff. CI runs both on every push and pull request.
- **Frontend:** Next.js under `apps/web` (ADR-003), not part of this decision.

## Consequences

- Business rules from the reference codebase can be ported as plain Python functions with unit tests, without a framework runtime.
- Each service runs as its own container on Azure Container Apps (spec ADR), so one framework per service adds no operational cost.
- Services share one dependency baseline through `crepro-common`. Changes to it must be versioned deliberately.
- If the team later needs a different language for a service, that service can be replaced behind the same event contract (`EventEnvelope`).
