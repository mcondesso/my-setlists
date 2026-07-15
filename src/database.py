"""Database utilities for session management and schema initialization."""

from sqlmodel import Session, SQLModel, create_engine

import src.models  # noqa: F401 — ensures all models are registered with SQLAlchemy
from src.core.config import settings

engine = create_engine(settings.database_url, echo=False)


def init_db() -> None:
    """Create all database tables defined in SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Yield a database session for use in FastAPI dependency injection."""
    with Session(engine) as session:
        yield session
