"""Database engine setup, session management and schema initialization."""

from sqlmodel import create_engine, Session, SQLModel

from src.core.config import settings

engine = create_engine(
    settings.database_url,
    echo=False,
)


def init_db() -> None:
    """Create all database tables defined in SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Yield a database session for use in FastAPI dependency injection."""
    with Session(engine) as session:
        yield session
