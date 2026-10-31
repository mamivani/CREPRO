"""API request/response DTOs for the tenant service."""

from crepro_tenant.models import TenantOnboardingStatus, TenantTier
from pydantic import BaseModel


class TenantCreate(BaseModel):
    name: str
    subdomain: str
    custom_domain: str | None = None
    tier: TenantTier = TenantTier.SHARED


class TenantUpdate(BaseModel):
    name: str | None = None
    custom_domain: str | None = None
    tier: TenantTier | None = None
    status: TenantOnboardingStatus | None = None
