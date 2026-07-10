"""Shared pytest fixtures for database-backed route tests."""

import pytest
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool


@pytest.fixture()
def session() -> Session:
    """Provide an isolated in-memory database session for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
