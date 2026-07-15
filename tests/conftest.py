"""Shared pytest fixtures for database-backed route tests."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from src.database import get_session
import src.app
from src.core.config import settings


@pytest.fixture(scope="session")
def test_engine():
    """
    Create an in-memory SQLite engine shared across the entire test session.

    StaticPool ensures the same in-memory database is reused across all
    connections, which is required for SQLite in-memory databases to persist
    between requests within a single test.
    """
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(test_engine) -> Session:
    """
    Provide an isolated database session for direct DB interaction tests.

    Uses the same test engine as the client fixture, so reset_db applies
    equally to both session-based and client-based tests.
    """
    with Session(test_engine) as session:
        yield session


@pytest.fixture(autouse=True)
def reset_db(test_engine):
    """
    Reset the database before each test by dropping and recreating all tables.

    Autouse ensures this runs automatically for every test without
    needing to be explicitly requested as a parameter.
    """
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)
    yield


@pytest.fixture
def client(test_engine):
    """
    Provide a TestClient with the database dependency overridden.

    Each test gets a fresh database state via the reset_db fixture,
    ensuring full isolation between tests.
    """

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    src.app.app.dependency_overrides[get_session] = override_get_session
    with TestClient(src.app.app) as test_client:
        yield test_client
    src.app.app.dependency_overrides.clear()
