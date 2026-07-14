"""Integration tests for the auth module."""

from fastapi import status
from fastapi.testclient import TestClient


def test_register_success(client: TestClient):
    """Test successful user registration."""
    # Prepare test data
    user_data = {
        "email": "test@example.com",
        "display_name": "Test User",
        "password": "securepassword123",
    }

    # Make the request
    response = client.post("/auth/register", json=user_data)

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
    client.post("/auth/register", json=user_data)

    # Try to register again with the same email
    response = client.post("/auth/register", json=user_data)

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
    client.post("/auth/register", json=user_data)

    # Prepare login data (OAuth2PasswordRequestForm expects username and password)
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"],
    }

    # Make the login request
    response = client.post("/auth/login", data=login_data)

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
    client.post("/auth/register", json=user_data)

    # Prepare incorrect login data
    login_data = {
        "username": user_data["email"],
        "password": "wrongpassword",
    }

    # Make the login request
    response = client.post("/auth/login", data=login_data)

    # Assert the response
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Incorrect email or password"
