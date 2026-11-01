from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Every field is read from an environment variable prefixed with CREPRO_."""

    model_config = SettingsConfigDict(env_prefix="CREPRO_", env_file=".env", extra="ignore")

    environment: str = "local"
    database_url: str = "postgresql://localhost:5432/crepro"
    redis_url: str = "redis://localhost:6379/0"
    servicebus_namespace: str | None = None
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "crepro"
    jwt_audience: str = "crepro-api"
    jwt_expiration_minutes: int = 60
    jwt_refresh_expiration_minutes: int = 10080  # 7 days
    opentelemetry_enabled: bool = False
    jaeger_host: str = "localhost"
    jaeger_port: int = 6831


@lru_cache
def get_settings() -> Settings:
    return Settings()