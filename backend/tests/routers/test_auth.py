"""Integration tests for the auth module."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.core.rate_limit import LOGIN_RATE_LIMIT, REGISTER_RATE_LIMIT, limiter
from tests.conftest import (
    AUTH_LOGIN_ENDPOINT,
    AUTH_REFRESH_ENDPOINT,
    AUTH_REGISTER_ENDPOINT,
    USERS_ME_ENDPOINT,
)


def test_register_success(client: TestClient):
    """Test successful user registration."""
    # Prepare test data
    user_data = {
        "email": "test@example.com",
        "display_name": "Test User",
        "password": "securepassword123",
    }

    # Make the request
    response = client.post(AUTH_REGISTER_ENDPOINT, json=user_data)

    # Assert the response
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["email"] == user_data["email"]
    assert response.json()["display_name"] == user_data["display_name"]
    assert "id" in response.json()
    assert "password" not in response.json()  # Ensure password is not exposed


def test_register_duplicate_email(client: TestClient):
    """Test registration with a duplicate email."""
    # Register a user first
    user_data = {
        "email": "duplicate@example.com",
        "display_name": "Duplicate User",
        "password": "securepassword123",
    }
    client.post(AUTH_REGISTER_ENDPOINT, json=user_data)

    # Try to register again with the same email
    response = client.post(AUTH_REGISTER_ENDPOINT, json=user_data)

    # Assert the response
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Email already registered"


def test_login_success(client: TestClient):
    """Test successful user login."""
    # Register a user first
    user_data = {
        "email": "login@example.com",
        "display_name": "Login User",
        "password": "securepassword123",
    }
    client.post(AUTH_REGISTER_ENDPOINT, json=user_data)

    # Prepare login data (OAuth2PasswordRequestForm expects username and password)
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"],
    }

    # Make the login request
    response = client.post(AUTH_LOGIN_ENDPOINT, data=login_data)

    # Assert the response
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_failed(client: TestClient):
    """Test failed user login with incorrect credentials."""
    # Register a user first
    user_data = {
        "email": "loginfail@example.com",
        "display_name": "Login Fail User",
        "password": "securepassword123",
    }
    client.post(AUTH_REGISTER_ENDPOINT, json=user_data)

    # Prepare incorrect login data
    login_data = {
        "username": user_data["email"],
        "password": "wrongpassword",
    }

    # Make the login request
    response = client.post(AUTH_LOGIN_ENDPOINT, data=login_data)

    # Assert the response
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.fixture
def rate_limiting_enabled():
    """Enable the (test-disabled) rate limiter for one test and reset it after."""
    limiter.enabled = True
    limiter.reset()
    try:
        yield
    finally:
        limiter.reset()
        limiter.enabled = False


def test_login_is_rate_limited(client: TestClient, rate_limiting_enabled):
    """After LOGIN_RATE_LIMIT attempts the endpoint returns 429."""
    limit = int(LOGIN_RATE_LIMIT.split("/")[0])
    login_data = {"username": "nobody@example.com", "password": "wrong"}

    statuses = [
        client.post(AUTH_LOGIN_ENDPOINT, data=login_data).status_code for _ in range(limit + 1)
    ]

    assert statuses[:limit] == [status.HTTP_401_UNAUTHORIZED] * limit
    assert statuses[limit] == status.HTTP_429_TOO_MANY_REQUESTS


def test_register_is_rate_limited(client: TestClient, rate_limiting_enabled):
    """After REGISTER_RATE_LIMIT attempts the endpoint returns 429."""
    limit = int(REGISTER_RATE_LIMIT.split("/")[0])

    statuses = [
        client.post(
            AUTH_REGISTER_ENDPOINT,
            json={
                "email": f"spam{i}@example.com",
                "display_name": "Spam",
                "password": "securepassword123",
            },
        ).status_code
        for i in range(limit + 1)
    ]

    assert statuses[:limit] == [status.HTTP_201_CREATED] * limit
    assert statuses[limit] == status.HTTP_429_TOO_MANY_REQUESTS


def test_refresh_returns_a_new_token(authenticated_client: TestClient):
    """A valid token can be exchanged for a new one."""
    response = authenticated_client.post(AUTH_REFRESH_ENDPOINT)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["token_type"] == "bearer"
    new_token = response.json()["access_token"]

    # The new token itself authenticates.
    me = authenticated_client.get(
        USERS_ME_ENDPOINT, headers={"Authorization": f"Bearer {new_token}"}
    )
    assert me.status_code == status.HTTP_200_OK


def test_refresh_requires_authentication(client: TestClient):
    """Refreshing without a token is rejected like any other protected route."""
    response = client.post(AUTH_REFRESH_ENDPOINT)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
