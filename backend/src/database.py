"""Database engine and session dependency.

The schema is owned by Alembic (see migrations/); nothing here creates
tables. Tests build their own engine in tests/conftest.py.
"""

from sqlmodel import Session, create_engine

import src.models  # noqa: F401 — registers all models so ORM relationships resolve
from src.core.config import settings

engine = create_engine(settings.database_url, echo=False)


def get_session():
    """Yield a database session for use in FastAPI dependency injection."""
    with Session(engine) as session:
        yield session
