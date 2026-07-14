"""Shared pytest fixtures for database-backed route tests."""

import os

import pytest
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

import dotenv

dotenv.load_dotenv()


@pytest.fixture
def base_url():
    """Return the base url to communicate with the app API"""
    app_port = os.getenv("APP_PORT")
    return f"http://localhost:{app_port}"


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
