"""Integration tests for the /songs endpoint."""

from fastapi import status
from fastapi.testclient import TestClient


def test_create_song(authenticated_client: TestClient):
    """Test creating a new song and adding it to a setlist."""
    # Create a setlist first
    setlist_data = {
        "name": "My Setlist",
        "description": "A cool setlist",
        "is_public": False,
    }
    response = authenticated_client.post("/setlists", json=setlist_data)
    setlist_id = response.json()["id"]

    # Create a song and add it to the setlist
    song_data = {
        "mbid": "mbid-1",
        "title": "Song Title",
        "artist": "Artist Name",
        "setlist_ids": [setlist_id],
    }
    response = authenticated_client.post("/songs", json=song_data)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["title"] == song_data["title"]
    assert response.json()["artist"] == song_data["artist"]
    assert response.json()["mbid"] == song_data["mbid"]
    assert "id" in response.json()


def test_create_song_reuses_existing_mbid(authenticated_client: TestClient):
    """Test that creating a song with an existing mbid reuses the song."""
    # Create a setlist
    setlist_data = {
        "name": "My Setlist",
        "description": "A cool setlist",
        "is_public": False,
    }
    response = authenticated_client.post("/setlists", json=setlist_data)
    setlist_id = response.json()["id"]

    # Create a song
    song_data = {
        "mbid": "mbid-2",
        "title": "Song Title",
        "artist": "Artist Name",
        "setlist_ids": [setlist_id],
    }
    response = authenticated_client.post("/songs", json=song_data)
    assert response.status_code == status.HTTP_201_CREATED
    first_song_id = response.json()["id"]

    # Create the same song again (same mbid)
    song_data = {
        "mbid": "mbid-2",
        "title": "Song Title",
        "artist": "Artist Name",
        "setlist_ids": [setlist_id],
    }
    response = authenticated_client.post("/songs", json=song_data)
    assert response.status_code == status.HTTP_201_CREATED
    second_song_id = response.json()["id"]

    # Verify the same song was reused
    assert first_song_id == second_song_id


def test_get_song(authenticated_client: TestClient):
    """Test fetching a single song."""
    # Create a song
    setlist_data = {
        "name": "My Setlist",
        "description": "A cool setlist",
        "is_public": False,
    }
    response = authenticated_client.post("/setlists", json=setlist_data)
    setlist_id = response.json()["id"]

    song_data = {
        "mbid": "mbid-3",
        "title": "Song Title",
        "artist": "Artist Name",
        "setlist_ids": [setlist_id],
    }
    response = authenticated_client.post("/songs", json=song_data)
    song_id = response.json()["id"]

    # Fetch the song
    response = authenticated_client.get(f"/songs/{song_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == song_id


def test_get_nonexistent_song(authenticated_client: TestClient):
    """Test fetching a non-existent song."""
    fake_id = "123e4567-e89b-12d3-a456-426614174000"
    response = authenticated_client.get(f"/songs/{fake_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Song not found"


def test_update_song(authenticated_client: TestClient):
    """Test updating a song's metadata."""
    # Create a setlist
    setlist_data = {
        "name": "My Setlist",
        "description": "A cool setlist",
        "is_public": False,
    }
    response = authenticated_client.post("/setlists", json=setlist_data)
    setlist_id = response.json()["id"]

    # Create a song
    song_data = {
        "mbid": "mbid-4",
        "title": "Song Title",
        "artist": "Artist Name",
        "setlist_ids": [setlist_id],
    }
    response = authenticated_client.post("/songs", json=song_data)
    song_id = response.json()["id"]

    # Update the song
    update_data = {
        "album": "Album Name",
        "release_year": 2023,
    }
    response = authenticated_client.patch(f"/songs/{song_id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["album"] == update_data["album"]
    assert response.json()["release_year"] == update_data["release_year"]


def test_update_song_setlist_memberships(authenticated_client: TestClient):
    """Test updating a song's setlist memberships."""
    # Create two setlists
    setlist1_data = {
        "name": "Setlist 1",
        "description": "First setlist",
        "is_public": False,
    }
    response = authenticated_client.post("/setlists", json=setlist1_data)
    setlist1_id = response.json()["id"]

    setlist2_data = {
        "name": "Setlist 2",
        "description": "Second setlist",
        "is_public": False,
    }
    response = authenticated_client.post("/setlists", json=setlist2_data)
    setlist2_id = response.json()["id"]

    # Create a song and add it to the first setlist
    song_data = {
        "mbid": "mbid-5",
        "title": "Song Title",
        "artist": "Artist Name",
        "setlist_ids": [setlist1_id],
    }
    response = authenticated_client.post("/songs", json=song_data)
    song_id = response.json()["id"]

    # Update the song to add it to the second setlist
    update_data = {
        "setlist_ids_to_add": [setlist2_id],
    }
    response = authenticated_client.patch(f"/songs/{song_id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK

    response = authenticated_client.get(f"/setlists/{setlist2_id}/songs")
    assert response.json()[0]["song_id"] == song_id


def test_user_cannot_update_song_without_access(
    authenticated_client: TestClient,
    authenticated_client_2: TestClient,
):
    """
    Test that User B (authenticated_client_2) cannot update a song
    created by User A (authenticated_client).
    """
    # User A creates a setlist
    setlist_data = {
        "name": "User A's Setlist",
        "description": "A setlist for User A",
        "is_public": False,
    }
    response = authenticated_client.post("/setlists", json=setlist_data)
    setlist_id = response.json()["id"]

    # User A creates a song and adds it to their setlist
    song_data = {
        "mbid": "mbid-6",
        "title": "Song Title",
        "artist": "Artist Name",
        "setlist_ids": [setlist_id],
    }
    response = authenticated_client.post("/songs", json=song_data)
    song_id = response.json()["id"]

    # User B tries to update the song (should fail)
    update_data = {"album": "Hacked Album"}
    response = authenticated_client_2.patch(f"/songs/{song_id}", json=update_data)

    # Assertions
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Not authorized to manage this song"
