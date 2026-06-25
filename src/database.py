"""Database utilities for session management and schema initialization."""

from sqlmodel import create_engine, Session, SQLModel
from src.core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=True)


def init_db():
    """Create all database tables defined on SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Yield a database session for use in FastAPI dependency injection."""
    with Session(engine) as session:
        yield session
