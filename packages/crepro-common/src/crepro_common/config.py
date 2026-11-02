from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Every field is read from an environment variable prefixed with CREPRO_."""

    model_config = SettingsConfigDict(env_prefix="CREPRO_", env_file=".env", extra="ignore")

    environment: str = "local"
    database_url: str = "postgresql+psycopg://crepro:crepro@localhost:5432/crepro"
    redis_url: str = "redis://localhost:6379/0"
    servicebus_namespace: str | None = None

    # JWT issuing/validation (15-day plan, Day 5). HS256 is enough for tokens this
    # platform both issues and validates itself; dev default is deliberately obvious
    # so it is never mistaken for a real secret.
    jwt_secret: str = "dev-insecure-secret-change-me-before-deploying-32+bytes"
    jwt_issuer: str = "crepro-identity"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_minutes: int = 20160  # 14 days

    # Base URL other services use to reach the tenant directory for Day 5's
    # custom-domain/subdomain tenant resolution.
    tenant_service_url: str = "http://tenant:8002"

    # OpenTelemetry basics (Day 5). Unset in Dev by default: tracing stays a no-op
    # until an OTLP collector endpoint is configured, so this never requires a
    # collector to be running locally.
    otel_exporter_endpoint: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
