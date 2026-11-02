"""OAuth/OIDC provider configuration, specific to the identity service only.

Kept separate from `crepro_common.config.Settings` because client IDs and the Microsoft
tenant are identity-service concerns, not something every service needs to read.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class IdentitySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CREPRO_IDENTITY_", env_file=".env", extra="ignore")

    # "common" accepts both personal and work/school Microsoft accounts (Vol 1 S6.2).
    microsoft_tenant: str = "common"
    microsoft_client_id: str = ""
    google_client_id: str = ""
    apple_client_id: str = ""


@lru_cache
def get_identity_settings() -> IdentitySettings:
    return IdentitySettings()
