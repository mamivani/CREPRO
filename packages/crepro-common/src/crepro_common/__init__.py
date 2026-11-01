"""Shared building blocks for CREPRO services."""

from crepro_common.app import create_app
from crepro_common.auth import TenantResolver, TokenClaims, TokenIssuer
from crepro_common.config import Settings, get_settings
from crepro_common.crud import build_crud_router
from crepro_common.entities import TenantScopedEntity
from crepro_common.events import EventEnvelope
from crepro_common.oauth import Provider, TokenResponse
from crepro_common.repository import EntityNotFoundError, InMemoryRepository
from crepro_common.tenancy import TenantContext, TenantNotSetError, current_tenant, require_tenant
from crepro_common.telemetry import get_tracer, init_tracing

__all__ = [
    "EntityNotFoundError",
    "EventEnvelope",
    "InMemoryRepository",
    "Provider",
    "Settings",
    "TenantContext",
    "TenantNotSetError",
    "TenantResolver",
    "TenantScopedEntity",
    "TokenClaims",
    "TokenIssuer",
    "TokenResponse",
    "build_crud_router",
    "create_app",
    "current_tenant",
    "get_settings",
    "get_tracer",
    "init_tracing",
    "require_tenant",
]

