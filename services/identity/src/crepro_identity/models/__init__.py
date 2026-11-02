"""Domain entities for the identity service: platform users and roles.

UserRole's maintenance-facing values are taken from the role catalog found across the
analyzed sample source's doctype permissions (system admin, property manager, and three
maintenance roles). Accountant and resident-portal are added since the platform also
needs ERP-adjacent and self-service roles the sample source left to its ERP backend.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from crepro_common import TenantScopedEntity
from pydantic import BaseModel


class UserRole(StrEnum):
    SYSTEM_ADMIN = "system_admin"
    PROPERTY_MANAGER = "property_manager"
    MAINTENANCE_MANAGER = "maintenance_manager"
    MAINTENANCE_SUPERVISOR = "maintenance_supervisor"
    MAINTENANCE_TECHNICIAN = "maintenance_technician"
    ACCOUNTANT = "accountant"
    RESIDENT_PORTAL = "resident_portal"


class UserStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"


class User(TenantScopedEntity):
    """A person who can authenticate against the platform."""

    email: str
    full_name: str
    role: UserRole
    status: UserStatus = UserStatus.INVITED
    last_login_at: datetime | None = None


class LocalCredential(BaseModel):
    """Password hash for a local-account user (15-day plan, Day 5).

    Kept out of `User` so it is never serialized by the user CRUD API's `response_model`.
    """

    user_id: UUID
    tenant_id: UUID
    password_hash: str
