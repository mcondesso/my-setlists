"""Application configuration loaded from environment and .env files."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed settings for database and application configuration."""

    model_config = SettingsConfigDict(env_file=".env")

    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DATABASE_URL: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    SECRET_KEY: str
    UVICORN_RELOAD: bool
    APP_PORT: int
    DISCOGS_API_TOKEN: str

    @property
    def database_url(self) -> str:
        """Return the database URL"""
        if self.ENVIRONMENT == "test":
            # Use in-memory sqlite db for tests
            return "sqlite:///:memory:"
        return self.DATABASE_URL


# The params are read from .env at runtime
settings = Settings()  # type: ignore
