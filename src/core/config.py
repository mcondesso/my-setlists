"""Application configuration loaded from environment and .env files."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Strongly typed settings for database and application configuration."""

    POSTGRES_HOSTNAME: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    SECRET_KEY: str
    UVICORN_RELOAD: bool

    @property
    def DATABASE_URL(self) -> str:
        """Build the SQLAlchemy database URL from configured environment values."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOSTNAME}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    class Config:
        """Configuration for Pydantic settings behavior."""

        env_file = ".env"


# The params are read from .env at runtime
settings = Settings()  # type: ignore
