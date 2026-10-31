"""Domain entities for the tenant service: the tenant (customer organization) directory.

This is the platform's control-plane service. It owns the master record for every
tenant_id referenced by TenantScopedEntity across all other services, plus onboarding
status, tier, and the subdomain/custom domain used to resolve a request to a tenant
(15-day plan, Day 5: custom domain > subdomain > claim). Because a Tenant row defines a
tenant rather than belonging to one, it does not extend TenantScopedEntity and is not
served through the generic tenant-scoped CRUD router.
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TenantTier(StrEnum):
    SHARED = "shared"
    DEDICATED = "dedicated"


class TenantOnboardingStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Tenant(BaseModel):
    """The master record for one customer organization using the platform."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    subdomain: str
    custom_domain: str | None = None
    tier: TenantTier = TenantTier.SHARED
    status: TenantOnboardingStatus = TenantOnboardingStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)
