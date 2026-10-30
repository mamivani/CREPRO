# ADR-013: Managed message broker: Azure Service Bus Standard

- **Status:** Proposed
- **Date:** 2026-10-30
- **Context:** The spec (Volume 1 §5.4, §7.7) requires events between services, retries, dead-letter queues, and per-entity ordering for ERP posting. The team is one person, so operating cost and operational burden matter most.

## Options considered

Prices are Azure retail consumption prices, South Central US, queried from the Azure Retail Prices API.

| Option | Monthly cost (low volume) | Topics (fan-out) | Dead-letter | Ordering / sessions | Dedupe | Fit |
|---|---|---|---|---|---|---|
| **Service Bus Standard** | ~$10 base (1 messaging unit, $0.01/hr); 13M operations included | Yes | Yes | Yes | Yes | **Chosen** |
| Service Bus Basic | $0.05 per 1M operations (no base) | No (queues only) | Yes | No | No | Too limited for fan-out |
| Event Grid Basic | $0.06 per 100K operations after 100K free | Yes (push) | Yes (to storage) | No | No | Good for outbound webhooks later |
| Event Grid Standard | $0.04/hr per throughput unit (~$29/month) | Yes | Yes | No | No | Costlier at this scale |
| Storage Queues | Lowest per-message cost | No | Manual poison queue | No | No | Lacks topics and dedupe |

## Decision

Use one **Azure Service Bus Standard** namespace in Dev, QA, UAT and Production, one topic per domain event family (for example `erp-events`, `lease-events`, `payment-events`), and one subscription per consumer.

Applications publish and subscribe through **Dapr pub/sub** (component type `pubsub.azure.servicebus.topics`). This keeps services broker-agnostic and matches the spec's Dapr support note (Volume 1 §9.4).

## Consequences

- Fixed cost of about $10/month per namespace, well inside the spec's $250–$1,000/month shared-SaaS budget (Volume 6 §13).
- Sessions keyed by `tenantId + entityId` give ordered ERP posting per entity.
- Dead-letter queues are monitored and replayed by the adapter's reconciliation job.
- Standard tier has a 256 KB message limit. Large documents go to Blob Storage and only the reference is published.
- Outbound customer webhooks (Volume 1 §7.7) may later use Event Grid Basic, which is cheaper per operation at high volume. This would be a separate ADR.
- Terraform owns the namespace, topics, and subscriptions (ADR-009). No portal changes.
