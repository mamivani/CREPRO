from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Every field is read from an environment variable prefixed with CREPRO_."""

    model_config = SettingsConfigDict(env_prefix="CREPRO_", env_file=".env", extra="ignore")

    environment: str = "local"
    database_url: str = "postgresql+psycopg://crepro:crepro@localhost:5432/crepro"
    redis_url: str = "redis://localhost:6379/0"
    servicebus_namespace: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
