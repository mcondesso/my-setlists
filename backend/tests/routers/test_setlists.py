"""TestClient coverage for the setlist routes and their response shape."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

import src.app
from src.core.rate_limit import RECOMMENDATION_REFRESH_RATE_LIMIT, limiter
from src.services.discogs import DiscogsSearchResult


def _create_setlist(client: TestClient, name: str = "Live Set", **fields) -> dict:
    response = client.post("/setlists/", json={"name": name, **fields})
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def _second_user_client() -> TestClient:
    """
    A second, independently-authenticated client sharing the same app
    (and thus the same overridden test database) as `client`/`authenticated_client`.
    """
    other = TestClient(src.app.app)
    other.post(
        "/auth/register",
        json={
            "email": "other@example.com",
            "display_name": "Other User",
            "password": "securepassword123",
        },
    )
    login = other.post(
        "/auth/login",
        data={"username": "other@example.com", "password": "securepassword123"},
    )
    other.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
    return other


def _create_song(client: TestClient, title: str) -> str:
    response = client.post("/songs/", json={"title": title, "artist": "Artist"})
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def test_create_setlist(authenticated_client: TestClient) -> None:
    body = _create_setlist(authenticated_client, "Encore", description="last songs")

    assert body["name"] == "Encore"
    assert body["owner_display_name"] == "Test User"
    assert body["is_library"] is False


def test_is_owner_reflects_who_owns_the_setlist(authenticated_client: TestClient) -> None:
    setlist_id = _create_setlist(authenticated_client, "Mine", is_public=True)["id"]
    other_client = _second_user_client()

    own_view = authenticated_client.get(f"/setlists/{setlist_id}")
    assert own_view.json()["is_owner"] is True

    other_view = other_client.get(f"/setlists/{setlist_id}")
    assert other_view.json()["is_owner"] is False

    own_list = authenticated_client.get("/setlists/").json()
    assert next(s for s in own_list if s["id"] == setlist_id)["is_owner"] is True

    other_list = other_client.get("/setlists/").json()
    assert next(s for s in other_list if s["id"] == setlist_id)["is_owner"] is False


def test_list_omits_entries(authenticated_client: TestClient) -> None:
    _create_setlist(authenticated_client)

    listed = authenticated_client.get("/setlists/")

    assert listed.status_code == status.HTTP_200_OK
    assert listed.json()
    assert all("entries" not in item for item in listed.json())


def test_list_is_paginated(authenticated_client: TestClient) -> None:
    for i in range(3):
        _create_setlist(authenticated_client, f"Set {i}")

    page = authenticated_client.get("/setlists/", params={"limit": 2})

    assert len(page.json()) == 2


def test_setlist_songs_are_returned_in_position_order(
    authenticated_client: TestClient,
) -> None:
    setlist_id = _create_setlist(authenticated_client)["id"]
    song_ids = [_create_song(authenticated_client, t) for t in ("First", "Second", "Third")]
    for song_id in song_ids:
        added = authenticated_client.post(f"/setlists/{setlist_id}/songs/{song_id}")
        assert added.status_code == status.HTTP_201_CREATED

    detail = authenticated_client.get(f"/setlists/{setlist_id}")
    assert [entry["position"] for entry in detail.json()["entries"]] == [1, 2, 3]

    by_position = authenticated_client.get(f"/setlists/{setlist_id}/songs")
    assert [e["song"]["title"] for e in by_position.json()] == ["First", "Second", "Third"]

    by_recent = authenticated_client.get(
        f"/setlists/{setlist_id}/songs", params={"order": "recent"}
    )
    assert by_recent.status_code == status.HTTP_200_OK
    assert {e["song"]["title"] for e in by_recent.json()} == {"First", "Second", "Third"}


def _add_songs(client: TestClient, setlist_id: str, titles: list[str]) -> list[str]:
    song_ids = [_create_song(client, title) for title in titles]
    for song_id in song_ids:
        client.post(f"/setlists/{setlist_id}/songs/{song_id}")
    return song_ids


def test_reorder_setlist_songs(authenticated_client: TestClient) -> None:
    setlist_id = _create_setlist(authenticated_client)["id"]
    a, b, c = _add_songs(authenticated_client, setlist_id, ["A", "B", "C"])

    response = authenticated_client.put(
        f"/setlists/{setlist_id}/songs/order", json={"song_ids": [c, a, b]}
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    detail = authenticated_client.get(f"/setlists/{setlist_id}")
    assert [e["song"]["title"] for e in detail.json()["entries"]] == ["C", "A", "B"]
    assert [e["position"] for e in detail.json()["entries"]] == [1, 2, 3]


def test_reorder_rejects_a_song_id_set_that_does_not_match(
    authenticated_client: TestClient,
) -> None:
    setlist_id = _create_setlist(authenticated_client)["id"]
    a, b, _c = _add_songs(authenticated_client, setlist_id, ["A", "B", "C"])

    # Missing one of the setlist's songs.
    response = authenticated_client.put(
        f"/setlists/{setlist_id}/songs/order", json={"song_ids": [b, a]}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    # A duplicate id (right length, wrong set).
    response = authenticated_client.put(
        f"/setlists/{setlist_id}/songs/order", json={"song_ids": [a, a, b]}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_reorder_requires_setlist_ownership(authenticated_client: TestClient) -> None:
    setlist_id = _create_setlist(authenticated_client, is_public=True)["id"]
    a, b = _add_songs(authenticated_client, setlist_id, ["A", "B"])

    response = _second_user_client().put(
        f"/setlists/{setlist_id}/songs/order", json={"song_ids": [b, a]}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_adding_the_same_song_twice_is_rejected(authenticated_client: TestClient) -> None:
    setlist_id = _create_setlist(authenticated_client)["id"]
    song_id = _create_song(authenticated_client, "Once")

    authenticated_client.post(f"/setlists/{setlist_id}/songs/{song_id}")
    again = authenticated_client.post(f"/setlists/{setlist_id}/songs/{song_id}")

    assert again.status_code == status.HTTP_400_BAD_REQUEST


def test_library_setlist_cannot_be_deleted(authenticated_client: TestClient) -> None:
    library = next(s for s in authenticated_client.get("/setlists/").json() if s["is_library"])

    response = authenticated_client.delete(f"/setlists/{library['id']}")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_changing_setlists_requires_authentication(client: TestClient) -> None:
    assert client.post("/setlists/", json={"name": "X"}).status_code == (
        status.HTTP_401_UNAUTHORIZED
    )


def test_logged_out_visitors_see_only_public_setlists(
    client: TestClient, authenticated_client: TestClient
) -> None:
    # `client` and `authenticated_client` share one TestClient whose auth
    # header the latter sets, so use a fresh client for the visitor.
    public = _create_setlist(authenticated_client, "Public Set", is_public=True)
    private = _create_setlist(authenticated_client, "Private Set")
    visitor = TestClient(src.app.app)

    listed = visitor.get("/setlists/")
    assert listed.status_code == status.HTTP_200_OK
    assert [s["name"] for s in listed.json()] == ["Public Set"]
    assert listed.json()[0]["is_owner"] is False

    detail = visitor.get(f"/setlists/{public['id']}")
    assert detail.status_code == status.HTTP_200_OK
    assert detail.json()["is_owner"] is False
    assert visitor.get(f"/setlists/{public['id']}/songs").status_code == status.HTTP_200_OK
    assert visitor.get(f"/setlists/{public['id']}/recommendation").status_code == (
        status.HTTP_200_OK
    )

    for path in ("", "/songs", "/recommendation"):
        assert visitor.get(f"/setlists/{private['id']}{path}").status_code == (
            status.HTTP_403_FORBIDDEN
        )


def test_logged_out_visitors_cannot_change_a_public_setlist(
    authenticated_client: TestClient,
) -> None:
    setlist_id = _create_setlist(authenticated_client, is_public=True)["id"]
    (song_id,) = _add_songs(authenticated_client, setlist_id, ["A"])
    visitor = TestClient(src.app.app)

    responses = [
        visitor.patch(f"/setlists/{setlist_id}", json={"name": "Hacked"}),
        visitor.delete(f"/setlists/{setlist_id}"),
        visitor.delete(f"/setlists/{setlist_id}/songs/{song_id}"),
        visitor.put(f"/setlists/{setlist_id}/songs/order", json={"song_ids": [song_id]}),
        visitor.post(f"/setlists/{setlist_id}/recommendation/refresh"),
    ]

    assert {r.status_code for r in responses} == {status.HTTP_401_UNAUTHORIZED}


def test_an_invalid_token_is_rejected_even_on_public_reads(
    authenticated_client: TestClient,
) -> None:
    # A stale token must not silently degrade to anonymous: the 401 is what
    # tells the frontend to log out.
    setlist_id = _create_setlist(authenticated_client, is_public=True)["id"]
    visitor = TestClient(src.app.app, headers={"Authorization": "Bearer not-a-real-token"})

    assert visitor.get(f"/setlists/{setlist_id}").status_code == status.HTTP_401_UNAUTHORIZED


def test_update_setlist_name_and_description(authenticated_client: TestClient) -> None:
    setlist = _create_setlist(authenticated_client, "Draft", description="wip")

    response = authenticated_client.patch(
        f"/setlists/{setlist['id']}",
        json={"name": "Final", "description": "ready to play"},
    )

    # Regression test: this 500ed with a ResponseValidationError — the
    # handler returned the bare ORM object instead of building a SetlistRead
    # (which needs owner_display_name, not a column on the model), and
    # nothing but a real HTTP round-trip could catch it.
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["name"] == "Final"
    assert body["description"] == "ready to play"
    assert body["owner_display_name"] == "Test User"

    refetched = authenticated_client.get(f"/setlists/{setlist['id']}")
    assert refetched.json()["name"] == "Final"


def test_update_setlist_clears_description_with_null(authenticated_client: TestClient) -> None:
    setlist = _create_setlist(authenticated_client, "Draft", description="wip")

    response = authenticated_client.patch(f"/setlists/{setlist['id']}", json={"description": None})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["description"] is None


def test_update_library_setlist_name_is_rejected(authenticated_client: TestClient) -> None:
    library = next(s for s in authenticated_client.get("/setlists/").json() if s["is_library"])

    response = authenticated_client.patch(f"/setlists/{library['id']}", json={"name": "Renamed"})

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_missing_setlist_returns_404(authenticated_client: TestClient) -> None:
    response = authenticated_client.patch(
        "/setlists/00000000-0000-0000-0000-000000000000", json={"name": "X"}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.fixture
def stub_recommender(monkeypatch):
    """Gemini suggests two songs, both of which Discogs confirms."""
    monkeypatch.setattr(
        "src.tasks.recommendations.suggest_songs",
        lambda songs, exclude=(): [("ABBA", "Dancing Queen"), ("Toto", "Africa")],
    )
    monkeypatch.setattr(
        "src.tasks.recommendations.find_track",
        lambda artist, title: DiscogsSearchResult(
            discogs_id="1-A1",
            title=title,
            artist=artist,
            album="Arrival",
            release_year=1976,
            discogs_url=None,
            thumbnail=None,
            duration_ms=231000,
        ),
    )


def test_adding_a_song_generates_a_recommendation(
    authenticated_client: TestClient, stub_recommender
) -> None:
    setlist_id = _create_setlist(authenticated_client)["id"]

    _add_songs(authenticated_client, setlist_id, ["A"])

    # TestClient runs background tasks before returning, so the run is done.
    detail = authenticated_client.get(f"/setlists/{setlist_id}").json()
    assert detail["recommendation"]["status"] == "ready"
    assert detail["recommendation"]["title"] == "Dancing Queen"
    assert (
        authenticated_client.get(f"/setlists/{setlist_id}/recommendation").json()
        == (detail["recommendation"])
    )


def test_removing_a_song_regenerates_the_recommendation(
    authenticated_client: TestClient,
) -> None:
    setlist_id = _create_setlist(authenticated_client)["id"]
    (song_id,) = _add_songs(authenticated_client, setlist_id, ["A"])

    authenticated_client.delete(f"/setlists/{setlist_id}/songs/{song_id}")

    # The setlist is now empty, so the regenerated recommendation is empty.
    recommendation = authenticated_client.get(f"/setlists/{setlist_id}/recommendation").json()
    assert recommendation["status"] == "not_found"


def test_reordering_does_not_touch_the_recommendation(authenticated_client: TestClient) -> None:
    setlist_id = _create_setlist(authenticated_client)["id"]
    a, b = _add_songs(authenticated_client, setlist_id, ["A", "B"])
    before = authenticated_client.get(f"/setlists/{setlist_id}/recommendation").json()

    authenticated_client.put(f"/setlists/{setlist_id}/songs/order", json={"song_ids": [b, a]})

    after = authenticated_client.get(f"/setlists/{setlist_id}/recommendation").json()
    assert after == before


def test_a_setlist_without_a_recommendation_returns_null(authenticated_client: TestClient) -> None:
    setlist_id = _create_setlist(authenticated_client)["id"]

    assert authenticated_client.get(f"/setlists/{setlist_id}").json()["recommendation"] is None
    assert authenticated_client.get(f"/setlists/{setlist_id}/recommendation").json() is None


def test_refresh_returns_pending_then_a_different_song(
    authenticated_client: TestClient, stub_recommender
) -> None:
    setlist_id = _create_setlist(authenticated_client)["id"]
    _add_songs(authenticated_client, setlist_id, ["A"])

    response = authenticated_client.post(f"/setlists/{setlist_id}/recommendation/refresh")

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["status"] == "pending"
    # Refresh avoids the current recommendation (Dancing Queen).
    final = authenticated_client.get(f"/setlists/{setlist_id}/recommendation").json()
    assert (final["status"], final["title"]) == ("ready", "Africa")


def test_only_the_owner_can_refresh_but_viewers_can_read(authenticated_client: TestClient) -> None:
    setlist_id = _create_setlist(authenticated_client, is_public=True)["id"]
    other_client = _second_user_client()

    refresh = other_client.post(f"/setlists/{setlist_id}/recommendation/refresh")
    read = other_client.get(f"/setlists/{setlist_id}/recommendation")

    assert refresh.status_code == status.HTTP_403_FORBIDDEN
    assert read.status_code == status.HTTP_200_OK


def test_a_private_setlists_recommendation_is_not_readable_by_others(
    authenticated_client: TestClient,
) -> None:
    setlist_id = _create_setlist(authenticated_client)["id"]

    response = _second_user_client().get(f"/setlists/{setlist_id}/recommendation")

    assert response.status_code == status.HTTP_403_FORBIDDEN


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


def test_refresh_is_rate_limited(authenticated_client: TestClient, rate_limiting_enabled) -> None:
    # Each refresh spends Gemini free-tier quota.
    setlist_id = _create_setlist(authenticated_client)["id"]
    limit = int(RECOMMENDATION_REFRESH_RATE_LIMIT.split("/")[0])

    statuses = [
        authenticated_client.post(f"/setlists/{setlist_id}/recommendation/refresh").status_code
        for _ in range(limit + 1)
    ]

    assert statuses[:limit] == [status.HTTP_202_ACCEPTED] * limit
    assert statuses[limit] == status.HTTP_429_TOO_MANY_REQUESTS
