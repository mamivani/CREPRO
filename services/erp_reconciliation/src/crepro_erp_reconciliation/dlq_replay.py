"""DLQ (Dead-Letter Queue) event replay logic."""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from .models import DLQReplayReport

logger = logging.getLogger(__name__)

MAX_REPLAY_ATTEMPTS = 2


async def replay_dlq_events(
    tenant_id: UUID,
    dlq_repo,
    adapter_client,
    max_age_hours: int = 24,
) -> DLQReplayReport:
    """
    Attempt to recover events from the dead-letter queue.

    Queries pending DLQ events and asks the adapter service to repost each one.
    Events that still fail after MAX_REPLAY_ATTEMPTS replays are escalated to manual review.

    Args:
        tenant_id: Tenant to process
        dlq_repo: Async DLQ event repository (PostgresDLQRepo)
        adapter_client: Adapter service client (has repost_entity)
        max_age_hours: Only replay events younger than this (default: 24 hours)

    Returns:
        DLQReplayReport with results
    """
    replay_started_at = datetime.utcnow()
    dlq_events_attempted = 0
    dlq_events_recovered = 0
    dlq_events_manual_review = 0

    try:
        # Get events routed to DLQ in the last max_age_hours
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        pending_dlq_events = await dlq_repo.get_pending_events(
            tenant_id=tenant_id,
            routed_after=cutoff_time,
            status="PENDING",
        )

        logger.info(f"DLQ replay: found {len(pending_dlq_events)} pending events for tenant {tenant_id}")

        for dlq_event in pending_dlq_events:
            dlq_events_attempted += 1

            try:
                logger.info(
                    f"DLQ replay: re-posting event {dlq_event.original_event_id} "
                    f"(entity {dlq_event.entity_id})"
                )

                success, _erp_docid = await adapter_client.repost_entity(
                    dlq_event.tenant_id,
                    dlq_event.entity_id,
                    dlq_event.external_doctype,
                    dlq_event.original_payload,
                )

                if success:
                    await dlq_repo.update(
                        dlq_event.id,
                        status="RECOVERED",
                        last_retry_at=datetime.utcnow(),
                    )
                    dlq_events_recovered += 1
                    logger.info(f"DLQ replay: successfully recovered event {dlq_event.original_event_id}")

                else:
                    replay_attempts = (dlq_event.retry_count or 0) + 1

                    if replay_attempts >= MAX_REPLAY_ATTEMPTS:
                        await dlq_repo.update(
                            dlq_event.id,
                            status="MANUAL_REVIEW_REQUIRED",
                            retry_count=replay_attempts,
                            last_retry_at=datetime.utcnow(),
                        )
                        dlq_events_manual_review += 1
                        logger.warning(
                            f"DLQ replay: event {dlq_event.original_event_id} exhausted retries; "
                            f"escalating to manual review"
                        )

                    else:
                        await dlq_repo.update(
                            dlq_event.id,
                            retry_count=replay_attempts,
                            last_retry_at=datetime.utcnow(),
                        )
                        logger.info(
                            f"DLQ replay: event {dlq_event.original_event_id} re-queued; "
                            f"retry {replay_attempts}/{MAX_REPLAY_ATTEMPTS}"
                        )

            except Exception as e:
                logger.error(f"Error replaying DLQ event {dlq_event.original_event_id}: {e}", exc_info=True)

                await dlq_repo.update(
                    dlq_event.id,
                    status="MANUAL_REVIEW_REQUIRED",
                    last_retry_at=datetime.utcnow(),
                )
                dlq_events_manual_review += 1

    except Exception as e:
        logger.error(f"Error during DLQ replay for tenant {tenant_id}: {e}", exc_info=True)
        raise

    replay_completed_at = datetime.utcnow()

    report = DLQReplayReport(
        tenant_id=tenant_id,
        replay_started_at=replay_started_at,
        replay_completed_at=replay_completed_at,
        dlq_events_attempted=dlq_events_attempted,
        dlq_events_recovered=dlq_events_recovered,
        dlq_events_manual_review=dlq_events_manual_review,
    )

    logger.info(
        f"DLQ replay complete for tenant {tenant_id}: "
        f"attempted={dlq_events_attempted}, recovered={dlq_events_recovered}, "
        f"manual_review={dlq_events_manual_review}"
    )

    return report
