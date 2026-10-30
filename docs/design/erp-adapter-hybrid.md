# ERP Adapter: Hybrid Sync Design

**Upstream ERP:** ERPNext v15.124.3 (frappe/erpnext commit `9f33fd5d32ae8a75156b2e7c2f8be02503fcc248`), vendored under [vendor/erpnext](../../vendor/erpnext).

## 1. Purpose

The ERP Adapter is the only component allowed to call ERPNext (spec Volume 1 §7.2). It copies financial records from the platform into ERPNext. The platform stays the system of record for operations; ERPNext is the system of record for the general ledger, AR and AP (spec Volume 1 §5.1, Volume 2 §18).

## 2. Hybrid model

The adapter combines two patterns from the spec:

| Path | Spec pattern | Trigger | Purpose |
|---|---|---|---|
| **Push (event-driven)** | Pattern 2 (events) | Domain event such as `InvoiceGenerated`, `PaymentPosted`, `LeaseExecuted` | Near-real-time posting, normally within seconds |
| **Pull (scheduled reconciliation)** | Pattern 3 (scheduled sync, ERPNext only) | Container Apps Job every 15 minutes, plus a nightly full pass | Repairs anything the push path missed: dead letters, outages, and ERPNext-side changes |

Both paths use the same posting code, so behavior is identical whichever path runs.

## 3. Components

```
Domain service ──(outbox row, same DB transaction)──► Outbox relay
                                                         │ Dapr pub/sub
                                                         ▼
                                              Service Bus topic (erp-events)
                                                         │ subscription erp-adapter
                                                         ▼
                                                    ERP Adapter
                                                         │ REST /api/resource
                                                         ▼
                                                      ERPNext
                                                         ▲
                                  Reconciliation job ────┘ (reads platform API and ERPNext, fixes drift)
```

- **Outbox table** in each domain service's PostgreSQL database. The domain change and its event row commit in one transaction (spec Volume 1 §11.6: no partial transactions).
- **Outbox relay** publishes outbox rows to Dapr and marks them sent. Delivery is at-least-once, so consumers must be idempotent.
- **ERP Adapter** consumes `erp-events`, maps each event to an ERPNext document, and writes its own adapter ledger.
- **Adapter ledger** (PostgreSQL) records `tenantId`, `platformEntityId`, `erpDoctype`, `erpName`, `payloadHash`, `status`, `attempts`, `lastError`. It is the adapter's own audit trail, separate from Frappe's `Version` doctype, which does not guarantee the spec's 7-year retention (Volume 1 §6.9).

## 4. Mapping (ERPNext doctypes)

| Platform event | ERPNext doctype (path in frappe/erpnext) | Notes |
|---|---|---|
| `CustomerUpserted` | `selling/doctype/customer` | Residents and guests |
| `VendorUpserted` | `buying/doctype/supplier` | Vendors |
| `InvoiceGenerated` | `accounts/doctype/sales_invoice` | Rent and fees |
| `PaymentPosted` | `accounts/doctype/payment_entry` | Linked to Sales Invoice |
| `DepositRecorded`, `AdjustmentPosted` | `accounts/doctype/journal_entry` | Deposits and manual adjustments |
| `PaymentMethodConfigured` | `accounts/doctype/mode_of_payment` | ACH, card, check |

ERPNext does **not** receive reservations, properties, meters, documents or maintenance (Volume 2 §18). Those stay in their owning services.

## 5. Idempotency

- Every ERPNext document has a custom field `platform_id` (UUID of the platform entity). The adapter looks up by `platform_id` before creating, so a retry updates instead of duplicating.
- Event `id` is recorded in the adapter ledger. Re-delivered events with the same `id` and `payloadHash` are acknowledged without a write.
- Changes to an already-posted document are applied as amendments, never by deleting submitted ERPNext documents.

## 6. Ordering and failure handling

- Service Bus session ID = `tenantId:platformEntityId`. Events for one entity are processed in order; different entities run in parallel.
- Retry policy: 5 attempts with exponential back-off, then the message moves to the dead-letter queue.
- Dead letters are reviewed by the reconciliation job, which replays them after the cause is fixed. Alerts fire on any dead letter (Volume 1 §10.6, High).
- If ERPNext is down, events wait in the topic subscription (retention set in Terraform within the Standard tier limit). Push resumes automatically when ERPNext recovers.

## 7. Reconciliation job

- Container Apps Job, every 15 minutes, scans platform records changed since the last watermark and compares them with ERPNext by `platform_id`. It also checks ERPNext's `modified` field for changes that did not come from the platform.
- Missing or mismatched records are re-posted through the same code path as push.
- Nightly full pass covers the last 90 days. The job writes a summary metric (rows checked, repaired, failed) to Azure Monitor.

## 8. Tenancy

Each tenant maps to an ERPNext target in an adapter-owned table:

- **Shared tier:** one ERPNext site, one ERPNext Company per tenant. Lowest cost.
- **Dedicated tier:** one ERPNext site per tenant (Volume 1 §9.6).

This mapping is an open decision (see §10).

## 9. Security

- The adapter is the only holder of ERPNext credentials. Each tenant's API key and secret are stored in Azure Key Vault and read at runtime through managed identity (Volume 1 §6.8).
- Requests carry tenant context from the JWT (`tenantId`), and the adapter checks it against the mapping table before any ERPNext call (Volume 1 §6.6).
- ERPNext is reachable only from the private Container Apps network (Volume 1 §4.3).
- Logs include `tenantId`, `service`, `requestId` and `correlationId` (Volume 1 §10.4).

## 10. Open items to verify in the spike

1. Exact token header format in `frappe/frappe/auth.py` (not confirmed in this review).
2. Whether `frappe/payments` (`stripe_settings`) is used at all. Current recommendation: no. The Payment Service calls Stripe directly and the adapter posts the resulting Payment Entry.
3. Tenancy mapping: per-site or per-Company for the shared tier.
4. Maximum event retention in the Standard tier for the adapter subscription.

## 11. Acceptance criteria

- Posting a `PaymentPosted` event creates one Payment Entry linked to its Sales Invoice, and a second delivery creates no duplicate.
- Stopping ERPNext for 30 minutes and restarting it results in all events posted with no manual step.
- A deliberately corrupted ERPNext record is repaired by the next reconciliation run.
- A cross-tenant test confirms that tenant A's event cannot write to tenant B's ERPNext target.
