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


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://api.discogs.com/database/search")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


@pytest.mark.parametrize("status_code", [401, 403])
def test_search_songs_reports_a_bad_token_clearly(monkeypatch, status_code) -> None:
    def raise_auth_error(query: str):
        raise _http_status_error(status_code)

    monkeypatch.setattr(songs_router, "search_discogs", raise_auth_error)

    with pytest.raises(HTTPException) as exc_info:
        songs_router.search_songs(q="wish you were here", current_user=_USER)

    assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY
    assert "DISCOGS_API_TOKEN" in exc_info.value.detail


def test_search_songs_reports_discogs_rate_limiting_clearly(monkeypatch) -> None:
    def raise_rate_limited(query: str):
        raise _http_status_error(429)

    monkeypatch.setattr(songs_router, "search_discogs", raise_rate_limited)

    with pytest.raises(HTTPException) as exc_info:
        songs_router.search_songs(q="wish you were here", current_user=_USER)

    assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY
    assert "rate limit" in exc_info.value.detail.lower()


def test_search_songs_falls_back_to_a_generic_message(monkeypatch) -> None:
    def raise_server_error(query: str):
        raise _http_status_error(503)

    monkeypatch.setattr(songs_router, "search_discogs", raise_server_error)

    with pytest.raises(HTTPException) as exc_info:
        songs_router.search_songs(q="wish you were here", current_user=_USER)

    assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY
    assert exc_info.value.detail == "The Discogs search is currently unavailable."


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
