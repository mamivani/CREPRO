"""Shared building blocks for CREPRO services."""

from crepro_common.app import create_app
from crepro_common.config import Settings, get_settings
from crepro_common.crud import build_crud_router
from crepro_common.entities import TenantScopedEntity
from crepro_common.events import EventEnvelope
from crepro_common.models import OutboxEntry, OutboxEntryStatus
from crepro_common.outbox import create_outbox_entry, get_pending_outbox_entries, mark_failed, mark_published
from crepro_common.repository import EntityNotFoundError, InMemoryRepository
from crepro_common.security import InvalidTokenError, TokenClaims, TokenType, decode_token, issue_token_pair
from crepro_common.tenancy import TenantContext, TenantNotSetError, current_tenant, require_tenant

__all__ = [
    "EntityNotFoundError",
    "EventEnvelope",
    "InMemoryRepository",
    "InvalidTokenError",
    "OutboxEntry",
    "OutboxEntryStatus",
    "Settings",
    "TenantContext",
    "TenantNotSetError",
    "TenantScopedEntity",
    "TokenClaims",
    "TokenType",
    "build_crud_router",
    "create_app",
    "create_outbox_entry",
    "current_tenant",
    "decode_token",
    "get_pending_outbox_entries",
    "get_settings",
    "issue_token_pair",
    "mark_failed",
    "mark_published",
    "require_tenant",
]
