"""Tests for the Discogs client's master-to-track expansion and matching."""

import httpx
import pytest

from src.services import discogs


def _search_response(results: list[dict]) -> httpx.Response:
    request = httpx.Request("GET", f"{discogs.DISCOGS_API_URL}/database/search")
    return httpx.Response(200, json={"results": results}, request=request)


def _master_response(master_id: int, tracklist: list[dict]) -> httpx.Response:
    request = httpx.Request("GET", f"{discogs.DISCOGS_API_URL}/masters/{master_id}")
    return httpx.Response(200, json={"tracklist": tracklist}, request=request)


def _fake_get_factory(search_results: list[dict], masters: dict[int, list[dict]]):
    def fake_get(url, headers=None, params=None, timeout=None):
        if url.endswith("/database/search"):
            return _search_response(search_results)
        for master_id, tracklist in masters.items():
            if url.endswith(f"/masters/{master_id}"):
                return _master_response(master_id, tracklist)
        raise AssertionError(f"unexpected URL requested: {url}")

    return fake_get


def test_returns_the_matching_track_rather_than_the_album(monkeypatch) -> None:
    # Regression test for the original complaint: searching "Darkside Heart"
    # used to return the "Psychic" album itself, not the "Heart" track on it.
    monkeypatch.setattr(
        discogs.httpx,
        "get",
        _fake_get_factory(
            search_results=[
                {
                    "id": 604361,
                    "title": "Darkside (22) - Psychic",
                    "year": "2013",
                    "thumb": "https://i.discogs.com/psychic.jpg",
                    "uri": "/master/604361-Darkside-Psychic",
                }
            ],
            masters={
                604361: [
                    {"position": "A1", "type_": "track", "title": "Golden Arrow"},
                    {"position": "B2", "type_": "track", "title": "Heart"},
                    {"position": "B3", "type_": "track", "title": "Paper Trails"},
                ]
            },
        ),
    )

    results = discogs.search_discogs("Darkside Heart", limit=1)

    assert len(results) == 1
    result = results[0]
    assert result.title == "Heart"
    assert result.artist == "Darkside"
    assert result.album == "Psychic"
    assert result.release_year == 2013
    assert result.thumbnail == "https://i.discogs.com/psychic.jpg"
    assert result.discogs_url == "https://www.discogs.com/master/604361-Darkside-Psychic"
    assert result.discogs_id == "604361-B2"


def test_strips_the_artist_disambiguation_suffix(monkeypatch) -> None:
    monkeypatch.setattr(
        discogs.httpx,
        "get",
        _fake_get_factory(
            search_results=[{"id": 1, "title": "Darkside (22) - Psychic", "uri": "/master/1"}],
            masters={1: [{"position": "B2", "type_": "track", "title": "Heart"}]},
        ),
    )

    results = discogs.search_discogs("Heart", limit=1)

    assert results[0].artist == "Darkside"


def test_skips_non_track_tracklist_entries(monkeypatch) -> None:
    monkeypatch.setattr(
        discogs.httpx,
        "get",
        _fake_get_factory(
            search_results=[{"id": 1, "title": "Artist - Album", "uri": "/master/1"}],
            masters={
                1: [
                    {"position": "", "type_": "heading", "title": "Side A"},
                    {"position": "A1", "type_": "track", "title": "Real Song"},
                ]
            },
        ),
    )

    results = discogs.search_discogs("Real Song", limit=5)

    assert [r.title for r in results] == ["Real Song"]


def test_tolerates_a_failing_master_lookup_and_uses_the_others(monkeypatch) -> None:
    def fake_get(url, headers=None, params=None, timeout=None):
        if url.endswith("/database/search"):
            return _search_response(
                [
                    {"id": 1, "title": "Artist - Broken Album", "uri": "/master/1"},
                    {"id": 2, "title": "Artist - Good Album", "uri": "/master/2"},
                ]
            )
        if url.endswith("/masters/1"):
            request = httpx.Request("GET", url)
            raise httpx.ConnectError("boom", request=request)
        if url.endswith("/masters/2"):
            return _master_response(2, [{"position": "A1", "type_": "track", "title": "Song"}])
        raise AssertionError(f"unexpected URL requested: {url}")

    monkeypatch.setattr(discogs.httpx, "get", fake_get)

    results = discogs.search_discogs("Song", limit=5)

    assert [r.title for r in results] == ["Song"]


def test_raises_when_the_initial_search_fails(monkeypatch) -> None:
    def fake_get(url, headers=None, params=None, timeout=None):
        request = httpx.Request("GET", url)
        raise httpx.ConnectError("no route to discogs", request=request)

    monkeypatch.setattr(discogs.httpx, "get", fake_get)

    with pytest.raises(httpx.ConnectError):
        discogs.search_discogs("anything")


def test_respects_limit_across_multiple_masters(monkeypatch) -> None:
    monkeypatch.setattr(
        discogs.httpx,
        "get",
        _fake_get_factory(
            search_results=[
                {"id": 1, "title": "Artist - Album One", "uri": "/master/1"},
                {"id": 2, "title": "Artist - Album Two", "uri": "/master/2"},
            ],
            masters={
                1: [{"position": "A1", "type_": "track", "title": "Wish You Were Here"}],
                2: [{"position": "A1", "type_": "track", "title": "Wish You Were Near"}],
            },
        ),
    )

    results = discogs.search_discogs("Wish You Were Here", limit=1)

    assert len(results) == 1
    assert results[0].title == "Wish You Were Here"


def test_prefers_the_artist_and_title_match_over_a_similar_bare_title(
    monkeypatch,
) -> None:
    # Regression test: scoring against the bare track title alone ranked
    # "Darkside Of The Heart" (by an unrelated artist) above "Heart" by
    # Darkside for the query "Darkside Heart", since its title textually
    # overlaps more of the query. Scoring the artist in too fixes this.
    monkeypatch.setattr(
        discogs.httpx,
        "get",
        _fake_get_factory(
            search_results=[
                {"id": 1, "title": "Paul Field Band - State Of Heart", "uri": "/master/1"},
                {"id": 2, "title": "Darkside (22) - Psychic", "uri": "/master/2"},
            ],
            masters={
                1: [{"position": "A1", "type_": "track", "title": "Darkside Of The Heart"}],
                2: [{"position": "B2", "type_": "track", "title": "Heart"}],
            },
        ),
    )

    results = discogs.search_discogs("Darkside Heart", limit=1)

    assert len(results) == 1
    assert results[0].artist == "Darkside"
    assert results[0].title == "Heart"


def test_parses_the_track_duration_into_milliseconds(monkeypatch) -> None:
    monkeypatch.setattr(
        discogs.httpx,
        "get",
        _fake_get_factory(
            search_results=[{"id": 1, "title": "Artist - Album", "uri": "/master/1"}],
            masters={
                1: [
                    {
                        "position": "A1",
                        "type_": "track",
                        "title": "Song",
                        "duration": "3:45",
                    }
                ]
            },
        ),
    )

    results = discogs.search_discogs("Song", limit=1)

    assert results[0].duration_ms == (3 * 60 + 45) * 1000


@pytest.mark.parametrize("duration", [None, "", "not-a-duration"])
def test_missing_or_unparseable_duration_is_none(monkeypatch, duration) -> None:
    track: dict = {"position": "A1", "type_": "track", "title": "Song"}
    if duration is not None:
        track["duration"] = duration
    monkeypatch.setattr(
        discogs.httpx,
        "get",
        _fake_get_factory(
            search_results=[{"id": 1, "title": "Artist - Album", "uri": "/master/1"}],
            masters={1: [track]},
        ),
    )

    results = discogs.search_discogs("Song", limit=1)

    assert results[0].duration_ms is None
