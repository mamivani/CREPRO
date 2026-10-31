"""Shared building blocks for CREPRO services."""

from crepro_common.app import create_app
from crepro_common.config import Settings, get_settings
from crepro_common.crud import build_crud_router
from crepro_common.entities import TenantScopedEntity
from crepro_common.events import EventEnvelope
from crepro_common.repository import EntityNotFoundError, InMemoryRepository
from crepro_common.tenancy import TenantContext, TenantNotSetError, current_tenant, require_tenant

__all__ = [
    "EntityNotFoundError",
    "EventEnvelope",
    "InMemoryRepository",
    "Settings",
    "TenantContext",
    "TenantNotSetError",
    "TenantScopedEntity",
    "build_crud_router",
    "create_app",
    "current_tenant",
    "get_settings",
    "require_tenant",
]
