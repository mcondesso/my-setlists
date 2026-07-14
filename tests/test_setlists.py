"""Integration tests for the /setlists endpoint."""

from fastapi import status
from fastapi.testclient import TestClient


def test_create_setlist(authenticated_client: TestClient):
    """Test creating a new setlist."""
    setlist_data = {
        "name": "My Setlist",
        "description": "A cool setlist",
        "is_public": False,
    }
    response = authenticated_client.post("/setlists", json=setlist_data)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == setlist_data["name"]
    assert response.json()["description"] == setlist_data["description"]
    assert response.json()["is_public"] == setlist_data["is_public"]
    assert response.json()["is_library"] is False
    assert "id" in response.json()


def test_get_setlists(authenticated_client: TestClient):
    """Test fetching all setlists for the current user."""
    # Create a setlist first
    setlist_data = {
        "name": "My Setlist",
        "description": "A cool setlist",
        "is_public": False,
    }
    response = authenticated_client.post("/setlists", json=setlist_data)
    setlist_id = response.json()["id"]

    # Fetch all setlists
    response = authenticated_client.get("/setlists")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2
    assert response.json()[1]["id"] == setlist_id


def test_get_setlist(authenticated_client: TestClient):
    """Test fetching a single setlist."""
    # Create a setlist
    setlist_data = {
        "name": "My Setlist",
        "description": "A cool setlist",
        "is_public": False,
    }
    response = authenticated_client.post("/setlists", json=setlist_data)
    setlist_id = response.json()["id"]

    # Fetch the setlist
    response = authenticated_client.get(f"/setlists/{setlist_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == setlist_id


def test_get_nonexistent_setlist(authenticated_client: TestClient):
    """Test fetching a non-existent setlist."""
    fake_id = "123e4567-e89b-12d3-a456-426614174000"
    response = authenticated_client.get(f"/setlists/{fake_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Setlist not found"


def test_update_setlist(authenticated_client: TestClient):
    """Test updating a setlist."""
    # Create a setlist
    setlist_data = {
        "name": "My Setlist",
        "description": "A cool setlist",
        "is_public": False,
    }
    response = authenticated_client.post("/setlists", json=setlist_data)
    setlist_id = response.json()["id"]

    # Update the setlist
    update_data = {"name": "Updated Setlist", "description": "An updated description"}
    response = authenticated_client.patch(f"/setlists/{setlist_id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == update_data["name"]
    assert response.json()["description"] == update_data["description"]


def test_update_library_setlist_fails(authenticated_client: TestClient):
    """Test that updating the library setlist fails."""
    # Fetch the library setlist
    response = authenticated_client.get("/setlists")
    library_setlist = next((s for s in response.json() if s["is_library"]), None)
    assert library_setlist is not None

    # Try to update the library setlist
    update_data = {"name": "Updated Library"}
    response = authenticated_client.patch(
        f"/setlists/{library_setlist['id']}", json=update_data
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert (
        response.json()["detail"]
        == "The library setlist's name and description cannot be changed"
    )


def test_delete_setlist(authenticated_client: TestClient):
    """Test deleting a setlist."""
    # Create a setlist
    setlist_data = {
        "name": "My Setlist",
        "description": "A cool setlist",
        "is_public": False,
    }
    response = authenticated_client.post("/setlists", json=setlist_data)
    setlist_id = response.json()["id"]

    # Delete the setlist
    response = authenticated_client.delete(f"/setlists/{setlist_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify the setlist is deleted
    response = authenticated_client.get(f"/setlists/{setlist_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_library_setlist_fails(authenticated_client: TestClient):
    """Test that deleting the library setlist fails."""
    # Fetch the library setlist
    response = authenticated_client.get("/setlists")
    library_setlist = next((s for s in response.json() if s["is_library"]), None)
    assert library_setlist is not None

    # Try to delete the library setlist
    response = authenticated_client.delete(f"/setlists/{library_setlist['id']}")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "The library setlist cannot be deleted"


def test_create_setlist_entry(authenticated_client: TestClient):
    """Test adding a song to a setlist."""
    # Create a setlist
    setlist_data = {
        "name": "My Setlist",
        "description": "A cool setlist",
        "is_public": False,
    }
    response = authenticated_client.post("/setlists", json=setlist_data)
    setlist_id = response.json()["id"]

    # Create a song
    song_data = {"mbid": "mbid-1", "title": "Song Title", "artist": "Artist Name"}
    response = authenticated_client.post("/songs", json=song_data)
    song_id = response.json()["id"]

    # Add the song to the setlist
    entry_data = {"setlist_id": setlist_id, "song_id": song_id, "position": 1}
    response = authenticated_client.post(
        f"/setlists/{setlist_id}/songs/{song_id}", json=entry_data
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["position"] == 1


def test_get_setlist_songs(authenticated_client: TestClient):
    """Test fetching all songs in a setlist."""
    # Create a setlist
    setlist_data = {
        "name": "My Setlist",
        "description": "A cool setlist",
        "is_public": False,
    }
    response = authenticated_client.post("/setlists", json=setlist_data)
    setlist_id = response.json()["id"]

    # Create a song
    song_data = {"mbid": "mbid-2", "title": "Song Title", "artist": "Artist Name"}
    response = authenticated_client.post("/songs", json=song_data)
    song_id = response.json()["id"]

    # Add the song to the setlist
    entry_data = {"setlist_id": setlist_id, "song_id": song_id, "position": 1}
    authenticated_client.post(
        f"/setlists/{setlist_id}/songs/{song_id}", json=entry_data
    )

    # Fetch the songs in the setlist
    response = authenticated_client.get(f"/setlists/{setlist_id}/songs")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["song_id"] == song_id
