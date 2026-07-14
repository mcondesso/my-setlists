"""Application configuration loaded from environment and .env files."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed settings for database and application configuration."""

    model_config = SettingsConfigDict(env_file=".env")

    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    POSTGRES_HOSTNAME: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    SECRET_KEY: str
    UVICORN_RELOAD: bool
    APP_PORT: int

    @property
    def database_url(self) -> str:
        """Return the database URL"""
        if self.ENVIRONMENT == "test":
            # Use in-memory sqlite db for tests
            return "sqlite:///:memory:"
        # Build from Postgres environment variables
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOSTNAME}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


# The params are read from .env at runtime
settings = Settings()  # type: ignore
