from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    """Standard envelope for every event published to the message broker.

    event_id is the consumer-side deduplication key, so redelivered messages are safe to process twice.
    """

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    tenant_id: UUID
    source: str
    schema_version: int = 1
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)
