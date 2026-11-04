# ERP Reconciliation Service

The ERP reconciliation service identifies and fixes discrepancies between the CREPRO platform and the external ERP system. It runs as an Azure Container Apps Job with two schedules:

- **Incremental scan**: Every 15 minutes (checks for recent modifications)
- **Full scan**: Nightly at 2 AM (validates complete consistency)

## Architecture

The service consists of three core modules:

### 1. Incremental Scan (`incremental_scan.py`)
**Schedule**: Every 15 minutes
**Purpose**: Find and fix recently modified records

**Algorithm**:
1. Query ERP for records modified since last scan
2. For each record:
   - Check if ledger entry exists (by platform_id)
   - If missing: create ledger entry and log discrepancy
   - If status=FAILED: attempt re-post
   - If status=POSTED: check for external modifications
3. Update last scan timestamp

**Discrepancies Detected**:
- MISSING_LEDGER: ERP record has no ledger entry
- REPOST_FAILED: Failed re-post attempt (escalated to manual review)
- EXTERNAL_MODIFICATION: ERP record modified externally after posting

### 2. Full Scan (`full_scan.py`)
**Schedule**: Nightly at 2 AM
**Purpose**: Comprehensive validation of all records

**Algorithm**:
1. Query ALL ERP records (not just recent)
2. Step 1: Check all ERP records have ledger entries
   - Orphaned records: create ledger or escalate
3. Step 2: Check all ledger entries have corresponding ERP records
   - Missing ERP records: mark as DELETED or escalate

**Discrepancies Detected**:
- ORPHANED_RECORD: ERP record with no ledger entry
- DELETED_IN_ERP: Ledger entry but ERP record is gone
- DELETED_BUT_EXISTS: Ledger marked DELETED but ERP still has active record

### 3. DLQ Replay (`dlq_replay.py`)
**Schedule**: Every 15 minutes (with incremental scan)
**Purpose**: Recover events from dead-letter queue

**Algorithm**:
1. Query pending DLQ events (routed in last 24 hours)
2. For each event:
   - Attempt re-post via post_to_erp_with_retry()
   - Success: mark as RECOVERED
   - Failure (1st attempt): keep PENDING for next retry
   - Failure (2nd attempt): mark for MANUAL_REVIEW_REQUIRED

**Exit Criteria**:
- Max 2 DLQ replay attempts per event
- Events escalated to ops team after 2 failures
- Max 24-hour retention (older events archived)

## Data Models

### ReconciliationDiscrepancy
```python
id: UUID                                    # Discrepancy ID
tenant_id: UUID                             # Tenant identifier
doctype: str                                # ERP document type (Customer, Invoice, etc.)
docid: str                                  # ERP document ID (CUST-001)
discrepancy_type: DiscrepancyType           # Type of discrepancy found
detected_at: datetime                       # When discovered
resolved: bool = False                      # Marked as resolved?
resolution_notes: str = ""                  # Operations notes
```

### ScanReport
```python
scan_type: str                              # "incremental" or "full"
tenant_id: UUID                             # Tenant scanned
started_at: datetime                        # Scan start time
completed_at: datetime                      # Scan end time
total_records_scanned: int                  # Number of records checked
discrepancies_found: int                    # Number of issues detected
items_fixed: int                            # Number of auto-fixed items
manual_review_required: int                 # Items needing ops intervention
discrepancies: list[ReconciliationDiscrepancy]  # Full discrepancy details
```

### DLQReplayReport
```python
tenant_id: UUID                             # Tenant processed
replay_started_at: datetime                 # Replay start time
replay_completed_at: datetime               # Replay end time
dlq_events_attempted: int                   # Total events attempted
dlq_events_recovered: int                   # Successfully recovered
dlq_events_manual_review: int               # Escalated for manual review
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest tests/ -v

# Run specific module tests
pytest tests/test_incremental_scan.py -v
pytest tests/test_full_scan.py -v
pytest tests/test_dlq_replay.py -v
```

**Test Coverage**:
- 5 incremental scan tests
- 6 full scan tests
- 6 DLQ replay tests
- **Total**: 17 tests, all passing

**Mock Infrastructure**:
- MockERPClient: Simulates ERP API
- MockLedgerRepo: Simulates adapter ledger database
- MockDLQRepo: Simulates Dapr DLQ topic
- MockAdapterClient: Simulates adapter service

## Deployment

### Docker

```bash
# Build image
docker build -t crepro-erp-reconciliation:latest .

# Run incremental scan
docker run \
  -e RECONCILIATION_MODE=INCREMENTAL \
  -e TENANT_ID=00000000-0000-0000-0000-000000000000 \
  crepro-erp-reconciliation:latest

# Run full scan
docker run \
  -e RECONCILIATION_MODE=FULL \
  -e TENANT_ID=00000000-0000-0000-0000-000000000000 \
  crepro-erp-reconciliation:latest
```

### Azure Container Apps Job

Deployed via Terraform with two scheduled jobs:

```hcl
resource "azurerm_container_app_job" "erp_reconciliation_incremental" {
  # Every 15 minutes (*/15 * * * *)
  schedule_trigger { cron_expression = "*/15 * * * *" }
}

resource "azurerm_container_app_job" "erp_reconciliation_full" {
  # Nightly at 2 AM (0 2 * * *)
  schedule_trigger { cron_expression = "0 2 * * *" }
}
```

## Integration with Day 12

The reconciliation service integrates with Day 12 (ERP Adapter) as follows:

### Idempotency + Retry + Reconciliation Stack

```
Event Flow:
1. Domain service creates entity → publishes to erp-events
2. ERP Adapter (Day 11/12):
   - Checks idempotency (platform_id custom field in ERP)
   - If not in ERP: calls post_to_erp_with_retry()
   - On max failure: routes to dead_letter_events topic

3. Reconciliation Service (Day 13):
   - Incremental scan (15 min): Re-attempts FAILED entries
   - Full scan (nightly): Validates complete consistency
   - DLQ replay (15 min): Attempts recovery of dead-lettered events
   - Manual escalation: Ops team reviews unrecoverable items
```

### AdapterLedgerEntry Fields Used

- `status`: POSTED, FAILED, DELETED, RECONCILED
- `attempts`: Retry count (incremented on each failure)
- `last_error`: Most recent failure reason
- `erp_docid`: ERP document ID (populated on success)
- `external_doctype`: ERP document type (Customer, Invoice, etc.)

### Database Schema

The reconciliation service queries:
- `adapter_ledger_entries`: Status tracking for all posted entities
- `dead_letter_events`: Events that failed all retries (Day 12)

## Monitoring & Alerts

### Key Metrics

- `reconciliation_scan_duration_seconds`: Time to complete scan
- `reconciliation_discrepancies_found_total`: Cumulative discrepancies
- `reconciliation_items_fixed_total`: Cumulative auto-fixes
- `reconciliation_manual_review_required_total`: Items escalated to ops
- `dlq_replay_recovery_rate_percent`: % of DLQ events recovered

### Alert Triggers

- Scan takes > 30 minutes (possible performance issue)
- Discrepancies found > 100 in single scan (data quality issue)
- Manual review items > 50 (need ops intervention)
- DLQ replay recovery rate < 50% (retry strategy may need tuning)

## Known Limitations

1. **Mock Client**: Current implementation uses mock ERP/ledger clients. Production deployment requires:
   - Real ERP HTTP client (via adapter service)
   - Real ledger repository (via database connection)
   - Real DLQ subscription (via Dapr pub/sub)

2. **No Automatic Repair**: Most discrepancies require manual ops review. Future enhancement:
   - Configurable auto-repair rules by discrepancy type
   - Audit trail for ops actions
   - Approval workflow for high-impact repairs

3. **Single-Tenant Design**: Current design processes one tenant per job run. Future enhancement:
   - Multi-tenant batch processing
   - Parallel scan for multiple tenants

4. **No Backoff Strategy**: DLQ replay uses immediate retry. Future enhancement:
   - Exponential backoff like Day 12 retry logic
   - Jitter to prevent thundering herd

## Future Work (Days 14-15)

- [ ] Deploy to Azure Container Apps
- [ ] Integrate with real ERP client (via adapter HTTP)
- [ ] Add Dapr pub/sub for events
- [ ] Create ops dashboard for monitoring
- [ ] Define manual review SLA & workflow
- [ ] Add alerting to Slack/email
- [ ] Implement audit logging for all repairs
- [ ] Performance optimize for large tenant volumes

## Related Documentation

- Day 11: [ERP Adapter Push Path with Idempotency](../erp_adapter/README.md)
- Day 12: [Retry Policy and DLQ Routing](../erp_adapter/README.md)
- Architecture: [Days 11-15 Roadmap](../../DAYS_11-15_AND_FRONTEND_ROADMAP.md)
