"""Tests for the background setlist-recommendation task."""

from uuid import uuid4

import pytest
from sqlmodel import Session

from src.models.recommendation import RecommendationStatus, SetlistRecommendation
from src.models.setlist import Setlist, SetlistEntry
from src.models.song import Song
from src.models.user import User
from src.services.discogs import DiscogsSearchResult
from src.services.gemini import GeminiNotConfiguredError
from src.tasks import recommendations


def _discogs_result(artist: str, title: str) -> DiscogsSearchResult:
    return DiscogsSearchResult(
        discogs_id="1-A1",
        title=title,
        artist=artist,
        album="Album",
        release_year=1990,
        discogs_url="https://www.discogs.com/master/1",
        thumbnail="https://i.discogs.com/thumb.jpg",
        duration_ms=200000,
    )


@pytest.fixture
def setlist(session: Session) -> Setlist:
    user = User(email="rec@example.com", display_name="Rec", password="x")
    session.add(user)
    session.flush()
    setlist = Setlist(user_id=user.id, name="Set")
    song = Song(artist="Queen", title="We Will Rock You")
    session.add_all([setlist, song])
    session.flush()
    session.add(SetlistEntry(setlist_id=setlist.id, song_id=song.id, position=1))
    session.commit()
    return setlist


def _pending(session: Session, setlist: Setlist, **fields) -> SetlistRecommendation:
    recommendation = SetlistRecommendation(
        setlist_id=setlist.id, status=RecommendationStatus.PENDING, **fields
    )
    session.add(recommendation)
    session.commit()
    return recommendation


def _run(session: Session, test_engine, recommendation: SetlistRecommendation) -> None:
    recommendations.update_recommendation(
        recommendation.setlist_id, recommendation.request_id, test_engine
    )
    session.expire_all()


def test_stores_the_first_suggestion_found_on_discogs(
    session, test_engine, setlist, monkeypatch
) -> None:
    monkeypatch.setattr(
        recommendations,
        "suggest_songs",
        lambda songs, exclude=(): [("Made Up", "Not Real"), ("ABBA", "Dancing Queen")],
    )
    monkeypatch.setattr(
        recommendations,
        "find_track",
        lambda artist, title: _discogs_result(artist, title) if artist == "ABBA" else None,
    )
    recommendation = _pending(session, setlist)

    _run(session, test_engine, recommendation)

    saved = session.get(SetlistRecommendation, setlist.id)
    assert saved.status == RecommendationStatus.READY
    assert (saved.artist, saved.title) == ("ABBA", "Dancing Queen")
    assert saved.duration_ms == 200000


def test_skips_songs_already_in_the_setlist_or_previously_recommended(
    session, test_engine, setlist, monkeypatch
) -> None:
    seen = {}

    def suggest(songs, exclude=()):
        seen.update(songs=songs, exclude=exclude)
        return [("queen", "we will rock you"), ("ABBA", "Dancing Queen"), ("Toto", "Africa")]

    monkeypatch.setattr(recommendations, "suggest_songs", suggest)
    monkeypatch.setattr(recommendations, "find_track", _discogs_result)
    recommendation = _pending(session, setlist, artist="ABBA", title="Dancing Queen")

    _run(session, test_engine, recommendation)

    assert seen["songs"] == [("Queen", "We Will Rock You")]
    assert seen["exclude"] == [("ABBA", "Dancing Queen")]
    saved = session.get(SetlistRecommendation, setlist.id)
    assert (saved.artist, saved.title) == ("Toto", "Africa")


def test_not_found_when_no_suggestion_is_on_discogs(
    session, test_engine, setlist, monkeypatch
) -> None:
    monkeypatch.setattr(recommendations, "suggest_songs", lambda songs, exclude=(): [("A", "B")])
    recommendation = _pending(session, setlist, artist="Old", title="Pick")

    _run(session, test_engine, recommendation)

    saved = session.get(SetlistRecommendation, setlist.id)
    assert saved.status == RecommendationStatus.NOT_FOUND
    assert saved.title is None


def test_empty_setlist_is_not_found_without_calling_gemini(
    session, test_engine, monkeypatch
) -> None:
    user = User(email="empty@example.com", display_name="E", password="x")
    session.add(user)
    session.flush()
    empty = Setlist(user_id=user.id, name="Empty")
    session.add(empty)
    session.commit()

    def suggest(songs, exclude=()):
        raise AssertionError("Gemini should not be called for an empty setlist")

    monkeypatch.setattr(recommendations, "suggest_songs", suggest)
    recommendation = _pending(session, empty)

    _run(session, test_engine, recommendation)

    assert session.get(SetlistRecommendation, empty.id).status == RecommendationStatus.NOT_FOUND


@pytest.mark.parametrize("error", [GeminiNotConfiguredError("no key"), RuntimeError("boom")])
def test_failures_are_stored_not_raised(session, test_engine, setlist, monkeypatch, error) -> None:
    def suggest(songs, exclude=()):
        raise error

    monkeypatch.setattr(recommendations, "suggest_songs", suggest)
    recommendation = _pending(session, setlist)

    _run(session, test_engine, recommendation)

    assert session.get(SetlistRecommendation, setlist.id).status == RecommendationStatus.FAILED


def test_a_superseded_request_does_nothing(session, test_engine, setlist, monkeypatch) -> None:
    def suggest(songs, exclude=()):
        raise AssertionError("a superseded run should not call Gemini")

    monkeypatch.setattr(recommendations, "suggest_songs", suggest)
    _pending(session, setlist)

    # A stale request id: some newer request has replaced it.
    recommendations.update_recommendation(setlist.id, uuid4(), test_engine)

    session.expire_all()
    assert session.get(SetlistRecommendation, setlist.id).status == RecommendationStatus.PENDING


def test_a_result_is_dropped_if_a_newer_request_arrives_mid_run(
    session, test_engine, setlist, monkeypatch
) -> None:
    # Regression guard for out-of-order runs: a newer request lands while
    # this run is waiting on Gemini, so this run's result must not win.
    recommendation = _pending(session, setlist)
    newer_request_id = uuid4()

    def suggest(songs, exclude=()):
        with Session(test_engine) as other:
            row = other.get(SetlistRecommendation, setlist.id)
            row.request_id = newer_request_id
            other.add(row)
            other.commit()
        return [("ABBA", "Dancing Queen")]

    monkeypatch.setattr(recommendations, "suggest_songs", suggest)
    monkeypatch.setattr(recommendations, "find_track", _discogs_result)

    _run(session, test_engine, recommendation)

    saved = session.get(SetlistRecommendation, setlist.id)
    assert saved.status == RecommendationStatus.PENDING
    assert saved.request_id == newer_request_id
    assert saved.title is None
