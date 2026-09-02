"""TestClient coverage for the song-links routes and their response shape."""

from fastapi import status
from fastapi.testclient import TestClient


def _create_song(client: TestClient) -> str:
    response = client.post("/songs/", json={"title": "Money", "artist": "Pink Floyd"})
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def test_add_link_without_url_round_trips(authenticated_client: TestClient) -> None:
    song_id = _create_song(authenticated_client)

    created = authenticated_client.post(
        f"/songs/{song_id}/links/spotify", json={"external_id": "track-123"}
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.json() == {
        "platform": "spotify",
        "external_id": "track-123",
        "url": None,
    }

    # A null url must not break serialization of the list or the parent song.
    links = authenticated_client.get(f"/songs/{song_id}/links")
    assert links.status_code == status.HTTP_200_OK
    assert links.json()[0]["url"] is None

    song = authenticated_client.get(f"/songs/{song_id}")
    assert song.status_code == status.HTTP_200_OK
    assert song.json()["links"][0]["external_id"] == "track-123"


def test_add_link_with_url(authenticated_client: TestClient) -> None:
    song_id = _create_song(authenticated_client)

    response = authenticated_client.post(
        f"/songs/{song_id}/links/bandcamp",
        json={"external_id": "b1", "url": "https://example.bandcamp.com/track/x"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["url"] == "https://example.bandcamp.com/track/x"


def test_duplicate_platform_link_is_rejected(authenticated_client: TestClient) -> None:
    song_id = _create_song(authenticated_client)
    authenticated_client.post(f"/songs/{song_id}/links/spotify", json={"external_id": "one"})

    second = authenticated_client.post(
        f"/songs/{song_id}/links/spotify", json={"external_id": "two"}
    )

    assert second.status_code == status.HTTP_400_BAD_REQUEST


def test_update_and_delete_link(authenticated_client: TestClient) -> None:
    song_id = _create_song(authenticated_client)
    authenticated_client.post(f"/songs/{song_id}/links/spotify", json={"external_id": "one"})

    updated = authenticated_client.put(
        f"/songs/{song_id}/links/spotify",
        json={"url": "https://open.spotify.com/track/one"},
    )
    assert updated.status_code == status.HTTP_200_OK
    assert updated.json()["url"] == "https://open.spotify.com/track/one"

    deleted = authenticated_client.delete(f"/songs/{song_id}/links/spotify")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert authenticated_client.get(f"/songs/{song_id}/links").json() == []


def test_link_on_missing_song_returns_404(authenticated_client: TestClient) -> None:
    response = authenticated_client.post(
        "/songs/00000000-0000-0000-0000-000000000000/links/spotify",
        json={"external_id": "x"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
