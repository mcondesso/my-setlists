"""Song route tests for behaviour not covered at the model level."""

import httpx
import pytest
from fastapi import HTTPException, status

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
