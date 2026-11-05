"""Tests for DLQ (Dead-Letter Queue) replay logic."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from crepro_erp_reconciliation.dlq_replay import replay_dlq_events


@pytest.mark.asyncio
async def test_dlq_replay_recovers_pending_events_successfully(
    tenant_id, dlq_repo, adapter_client
):
    """DLQ replay successfully recovers events that re-post successfully."""
    # Setup: Add pending DLQ event
    dlq_event = dlq_repo.add_event(
        tenant_id=tenant_id,
        status="PENDING",
        original_payload={"name": "Test Customer"},
    )
    adapter_client.success = True

    # Execute
    report = await replay_dlq_events(
        tenant_id=tenant_id,
        dlq_repo=dlq_repo,
        adapter_client=adapter_client,
    )

    # Assert
    assert report.dlq_events_attempted == 1
    assert report.dlq_events_recovered == 1
    assert report.dlq_events_manual_review == 0
    assert adapter_client.post_calls[0]["dlq_replay"] is True

    # Verify event status updated
    updated_event = dlq_repo.events[0]
    assert updated_event.status == "RECOVERED"


@pytest.mark.asyncio
async def test_dlq_replay_requeues_on_first_failure(tenant_id, dlq_repo, adapter_client):
    """DLQ replay re-queues events on first failure (max 2 attempts)."""
    # Setup: Add pending DLQ event
    dlq_event = dlq_repo.add_event(
        tenant_id=tenant_id,
        status="PENDING",
        dlq_replay_attempts=0,
    )
    adapter_client.success = False

    # Execute
    report = await replay_dlq_events(
        tenant_id=tenant_id,
        dlq_repo=dlq_repo,
        adapter_client=adapter_client,
    )

    # Assert
    assert report.dlq_events_attempted == 1
    assert report.dlq_events_recovered == 0
    assert report.dlq_events_manual_review == 0  # Still pending, not manual review yet

    # Verify event still PENDING with retry count incremented
    updated_event = dlq_repo.events[0]
    assert updated_event.status == "PENDING"
    assert updated_event.dlq_replay_attempts == 1


@pytest.mark.asyncio
async def test_dlq_replay_escalates_after_max_retries(
    tenant_id, dlq_repo, adapter_client
):
    """DLQ replay escalates to manual review after 2 failed attempts."""
    # Setup: Add event that has already failed once
    dlq_event = dlq_repo.add_event(
        tenant_id=tenant_id,
        status="PENDING",
        dlq_replay_attempts=1,  # Already failed once
    )
    adapter_client.success = False

    # Execute
    report = await replay_dlq_events(
        tenant_id=tenant_id,
        dlq_repo=dlq_repo,
        adapter_client=adapter_client,
    )

    # Assert
    assert report.dlq_events_attempted == 1
    assert report.dlq_events_recovered == 0
    assert report.dlq_events_manual_review == 1  # Escalated

    # Verify event status updated to MANUAL_REVIEW_REQUIRED
    updated_event = dlq_repo.events[0]
    assert updated_event.status == "MANUAL_REVIEW_REQUIRED"
    assert updated_event.dlq_replay_attempts == 2


@pytest.mark.asyncio
async def test_dlq_replay_only_processes_recent_events(
    tenant_id, dlq_repo, adapter_client
):
    """DLQ replay only processes events younger than max_age_hours."""
    # Setup: Add recent and old DLQ events
    recent_event = dlq_repo.add_event(
        tenant_id=tenant_id,
        status="PENDING",
        routed_at=datetime.utcnow(),
    )
    old_event = dlq_repo.add_event(
        tenant_id=tenant_id,
        status="PENDING",
        routed_at=datetime.utcnow() - timedelta(days=2),
    )
    adapter_client.success = True

    # Execute with max_age_hours=24
    report = await replay_dlq_events(
        tenant_id=tenant_id,
        dlq_repo=dlq_repo,
        adapter_client=adapter_client,
        max_age_hours=24,
    )

    # Assert
    assert report.dlq_events_attempted == 1  # Only recent event
    assert report.dlq_events_recovered == 1
    assert adapter_client.post_calls[0]["entity_id"] == recent_event.entity_id


@pytest.mark.asyncio
async def test_dlq_replay_handles_missing_events(tenant_id, dlq_repo, adapter_client):
    """DLQ replay handles case with no pending events."""
    # Execute
    report = await replay_dlq_events(
        tenant_id=tenant_id,
        dlq_repo=dlq_repo,
        adapter_client=adapter_client,
    )

    # Assert
    assert report.dlq_events_attempted == 0
    assert report.dlq_events_recovered == 0
    assert report.dlq_events_manual_review == 0


@pytest.mark.asyncio
async def test_dlq_replay_multiple_events_with_mixed_results(
    tenant_id, dlq_repo, adapter_client
):
    """DLQ replay handles multiple events with different outcomes."""
    # Setup: Add multiple events
    # 1. Will succeed
    event1 = dlq_repo.add_event(
        tenant_id=tenant_id,
        status="PENDING",
        entity_id=uuid4(),
    )

    # 2. Will fail once (re-queue)
    event2 = dlq_repo.add_event(
        tenant_id=tenant_id,
        status="PENDING",
        entity_id=uuid4(),
        dlq_replay_attempts=0,
    )

    # 3. Will fail twice (manual review)
    event3 = dlq_repo.add_event(
        tenant_id=tenant_id,
        status="PENDING",
        entity_id=uuid4(),
        dlq_replay_attempts=1,
    )

    # Mock adapter to fail for events 2 and 3
    async def mock_post_with_sequence(*args, **kwargs):
        entity_id = kwargs["entity_id"]
        if entity_id == event1.entity_id:
            return True, "CUST-001"
        else:
            return False, None

    adapter_client.post_to_erp_with_retry = mock_post_with_sequence

    # Execute
    report = await replay_dlq_events(
        tenant_id=tenant_id,
        dlq_repo=dlq_repo,
        adapter_client=adapter_client,
    )

    # Assert
    assert report.dlq_events_attempted == 3
    assert report.dlq_events_recovered == 1
    assert report.dlq_events_manual_review == 1

    # Verify statuses
    assert dlq_repo.events[0].status == "RECOVERED"
    assert dlq_repo.events[1].status == "PENDING"  # Re-queued
    assert dlq_repo.events[2].status == "MANUAL_REVIEW_REQUIRED"  # Escalated


@pytest.mark.asyncio
async def test_dlq_replay_escalates_to_manual_review_on_adapter_exception(
    tenant_id, dlq_repo, adapter_client
):
    """An unexpected error re-posting a DLQ event (e.g. adapter service down)
    must not abort the whole replay batch -- just that event, escalated for review."""
    dlq_repo.add_event(tenant_id=tenant_id, status="PENDING")

    async def boom(*args, **kwargs):
        raise RuntimeError("adapter service down")

    adapter_client.post_to_erp_with_retry = boom

    # Execute
    report = await replay_dlq_events(
        tenant_id=tenant_id,
        dlq_repo=dlq_repo,
        adapter_client=adapter_client,
    )

    # Assert
    assert report.dlq_events_attempted == 1
    assert report.dlq_events_recovered == 0
    assert report.dlq_events_manual_review == 1
    assert dlq_repo.events[0].status == "MANUAL_REVIEW_REQUIRED"


@pytest.mark.asyncio
async def test_dlq_replay_reraises_dlq_repo_errors(tenant_id, adapter_client):
    """DLQ replay logs and re-raises errors fetching pending events, rather than
    swallowing them -- it must not record a false 'clean' replay."""

    class BoomDLQRepo:
        def get_pending_events(self, **kwargs):
            raise RuntimeError("state store unreachable")

    with pytest.raises(RuntimeError, match="state store unreachable"):
        await replay_dlq_events(
            tenant_id=tenant_id,
            dlq_repo=BoomDLQRepo(),
            adapter_client=adapter_client,
        )
