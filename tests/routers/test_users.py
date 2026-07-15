"""User route tests covering profile read, update, and deletion behavior."""

from fastapi import status
from fastapi.testclient import TestClient

from tests.conftest import USERS_ME_ENDPOINT


def test_read_current_user(authenticated_client: TestClient):
    """Test fetching the current user's profile."""
    response = authenticated_client.get(USERS_ME_ENDPOINT)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == "user@example.com"
    assert response.json()["display_name"] == "Test User"
    assert "password" not in response.json()


def test_update_current_user(authenticated_client: TestClient):
    """Test updating the current user's display name."""
    # Prepare update data
    update_data = {"display_name": "Updated User"}

    # Make the PATCH request
    response = authenticated_client.patch(USERS_ME_ENDPOINT, json=update_data)

    # Assert the response
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["display_name"] == "Updated User"

    # Verify the update persisted
    response = authenticated_client.get(USERS_ME_ENDPOINT)
    assert response.json()["display_name"] == "Updated User"


def test_delete_current_user(authenticated_client: TestClient):
    """Test deleting the current user's account."""
    # Make the DELETE request
    response = authenticated_client.delete(USERS_ME_ENDPOINT)

    # Assert the response
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify the user is deleted
    response = authenticated_client.get(USERS_ME_ENDPOINT)
    assert (
        response.status_code == status.HTTP_401_UNAUTHORIZED
    )  # No longer authenticated
