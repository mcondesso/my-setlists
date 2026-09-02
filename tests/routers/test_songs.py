"""Song route tests for behaviour not covered at the model level."""

import httpx
import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from src.models.user import User
from src.routers import songs as songs_router

_USER = User(email="searcher@example.com", display_name="Searcher", password="secret")


def test_search_songs_maps_discogs_timeout_to_504(monkeypatch) -> None:
    def raise_timeout(query: str):
        raise httpx.ReadTimeout("discogs slow")

    monkeypatch.setattr(songs_router, "search_discogs", raise_timeout)

    with pytest.raises(HTTPException) as exc_info:
        songs_router.search_songs(q="wish you were here", current_user=_USER)

    assert exc_info.value.status_code == status.HTTP_504_GATEWAY_TIMEOUT


def test_search_songs_maps_discogs_failure_to_502(monkeypatch) -> None:
    def raise_connect_error(query: str):
        raise httpx.ConnectError("no route to discogs")

    monkeypatch.setattr(songs_router, "search_discogs", raise_connect_error)

    with pytest.raises(HTTPException) as exc_info:
        songs_router.search_songs(q="wish you were here", current_user=_USER)

    assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY


def _create_song(client: TestClient, title: str, artist: str = "Artist") -> dict:
    response = client.post("/songs/", json={"title": title, "artist": artist})
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def test_create_song_then_fetch_it(authenticated_client: TestClient) -> None:
    created = _create_song(authenticated_client, "Time")

    assert created["title"] == "Time"
    assert "id" in created

    response = authenticated_client.get(f"/songs/{created['id']}")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["artist"] == "Artist"
    assert body["links"] == []


def test_get_missing_song_returns_404(authenticated_client: TestClient) -> None:
    response = authenticated_client.get("/songs/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_list_songs_is_paginated_and_ordered(authenticated_client: TestClient) -> None:
    for title in ("Delta", "Alpha", "Charlie", "Bravo"):
        _create_song(authenticated_client, title)

    first = authenticated_client.get("/songs/", params={"limit": 2}).json()
    second = authenticated_client.get("/songs/", params={"limit": 2, "offset": 2}).json()

    assert [s["title"] for s in first] == ["Alpha", "Bravo"]
    assert [s["title"] for s in second] == ["Charlie", "Delta"]


def test_list_songs_rejects_out_of_range_limit(authenticated_client: TestClient) -> None:
    response = authenticated_client.get("/songs/", params={"limit": 0})

    assert response.status_code == 422
