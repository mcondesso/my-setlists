"""Tests for the background YouTube-link task."""

from uuid import uuid4

import pytest
from sqlmodel import Session, select

from src.models.song import Song
from src.models.song_link import Platform, SongLink
from src.tasks.youtube import fetch_and_save_youtube_link

_VIDEO = {
    "video_id": "dQw4w9WgXcQ",
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
}


def _youtube_link(session: Session, song_id) -> SongLink | None:
    return session.exec(
        select(SongLink).where(
            SongLink.song_id == song_id,
            SongLink.platform == Platform.YOUTUBE,
        )
    ).first()


@pytest.fixture
def song(session: Session) -> Song:
    song = Song(title="Song", artist="Artist")
    session.add(song)
    session.commit()
    session.refresh(song)
    return song


def test_saves_link_when_a_video_is_found(session, test_engine, song, monkeypatch) -> None:
    monkeypatch.setattr("src.tasks.youtube.find_top_youtube_video", lambda artist, title: _VIDEO)

    fetch_and_save_youtube_link(song.id, test_engine)

    link = _youtube_link(session, song.id)
    assert link is not None
    assert link.external_id == _VIDEO["video_id"]
    assert link.url == _VIDEO["url"]


def test_skips_when_a_youtube_link_already_exists(session, test_engine, song, monkeypatch) -> None:
    session.add(
        SongLink(
            song_id=song.id,
            platform=Platform.YOUTUBE,
            external_id="existing",
            url="https://youtu.be/existing",
        )
    )
    session.commit()

    lookups: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "src.tasks.youtube.find_top_youtube_video",
        lambda artist, title: lookups.append((artist, title)),
    )

    fetch_and_save_youtube_link(song.id, test_engine)

    assert lookups == []
    assert _youtube_link(session, song.id).external_id == "existing"


def test_no_op_when_no_video_is_found(session, test_engine, song, monkeypatch) -> None:
    monkeypatch.setattr("src.tasks.youtube.find_top_youtube_video", lambda artist, title: None)

    fetch_and_save_youtube_link(song.id, test_engine)

    assert _youtube_link(session, song.id) is None


def test_no_op_when_song_is_missing(session, test_engine, monkeypatch) -> None:
    called = False

    def _lookup(artist, title):
        nonlocal called
        called = True
        return _VIDEO

    monkeypatch.setattr("src.tasks.youtube.find_top_youtube_video", _lookup)

    fetch_and_save_youtube_link(uuid4(), test_engine)  # must not raise

    assert called is False
