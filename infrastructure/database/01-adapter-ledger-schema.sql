-- Adapter Ledger Schema for ERP Sync Audit Trail
-- 
-- Tables:
-- - adapter_ledger_entries: Audit trail of all ERP sync operations
-- - dlq_events: Dead-lettered events from failed ERP posts
-- - reconciliation_state: Tracking state for reconciliation jobs

-- Adapter Ledger Entries Table
CREATE TABLE IF NOT EXISTS adapter_ledger_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    platform_entity_id UUID NOT NULL,
    event_type VARCHAR(50),  -- domain event that caused the post; NULL for entries reconciliation creates/infers
    external_doctype VARCHAR(50) NOT NULL,  -- Customer, Invoice, etc.
    payload_hash VARCHAR(64),  -- SHA256 hash of original payload; NULL when there is no original domain event
    status VARCHAR(20) NOT NULL,  -- POSTED, FAILED, DELETED, RECONCILED
    attempts INT DEFAULT 0,  -- Retry attempt count
    last_error TEXT,  -- Last error message
    erp_docid VARCHAR(255),  -- External ERP document ID/name
    notes TEXT,  -- Free-text context, e.g. "Inferred from ERP during full scan"
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_adapter_ledger_tenant_id ON adapter_ledger_entries(tenant_id);
CREATE INDEX idx_adapter_ledger_platform_entity ON adapter_ledger_entries(platform_entity_id);
CREATE INDEX idx_adapter_ledger_status ON adapter_ledger_entries(status);
CREATE UNIQUE INDEX idx_adapter_ledger_platform_unique ON adapter_ledger_entries(tenant_id, platform_entity_id);
CREATE INDEX idx_adapter_ledger_created_at ON adapter_ledger_entries(created_at);
CREATE INDEX idx_adapter_ledger_updated_at ON adapter_ledger_entries(updated_at);

-- Dead-Lettered Events Table (for Day 12 DLQ)
CREATE TABLE IF NOT EXISTS dlq_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    event_id UUID NOT NULL UNIQUE,
    platform_entity_id UUID NOT NULL,
    external_doctype VARCHAR(50) NOT NULL,
    reason TEXT NOT NULL,  -- Why event was DLQ'd
    payload JSONB NOT NULL,  -- Original event payload
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',  -- PENDING, RECOVERED, MANUAL_REVIEW_REQUIRED
    retry_count INT DEFAULT 0,
    routed_at TIMESTAMP NOT NULL,
    last_retry_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Widen status for databases created before MANUAL_REVIEW_REQUIRED (23 chars) fit VARCHAR(20).
-- Widening a varchar is a no-op when the column is already at least this wide.
ALTER TABLE dlq_events ALTER COLUMN status TYPE VARCHAR(32);

-- Indexes for DLQ queries
CREATE INDEX idx_dlq_tenant_id ON dlq_events(tenant_id);
CREATE INDEX idx_dlq_status ON dlq_events(status);
CREATE INDEX idx_dlq_routed_at ON dlq_events(routed_at);
CREATE INDEX idx_dlq_created_at ON dlq_events(created_at);

-- Reconciliation State Table (for Day 13 tracking)
CREATE TABLE IF NOT EXISTS reconciliation_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL UNIQUE,
    last_incremental_scan TIMESTAMP,
    last_full_scan TIMESTAMP,
    last_dlq_replay TIMESTAMP,
    pending_manual_review_count INT DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Reconciliation Discrepancies Table (for Day 13 reporting)
CREATE TABLE IF NOT EXISTS reconciliation_discrepancies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    platform_entity_id UUID NOT NULL,
    external_doctype VARCHAR(50) NOT NULL,
    discrepancy_type VARCHAR(50) NOT NULL,  -- MISSING_LEDGER, ORPHANED_RECORD, DELETED_IN_ERP, etc.
    detected_at TIMESTAMP NOT NULL,
    resolved BOOLEAN DEFAULT FALSE,
    resolution_notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for discrepancy queries
CREATE INDEX idx_discrepancy_tenant_id ON reconciliation_discrepancies(tenant_id);
CREATE INDEX idx_discrepancy_type ON reconciliation_discrepancies(discrepancy_type);
CREATE INDEX idx_discrepancy_resolved ON reconciliation_discrepancies(resolved);
CREATE INDEX idx_discrepancy_detected_at ON reconciliation_discrepancies(detected_at);
