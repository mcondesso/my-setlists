"""Song route tests covering save, fetch, update, and deletion semantics."""

from fastapi import BackgroundTasks
from sqlmodel import Session, select

from src.models.setlist import Setlist, SetlistEntry
from src.models.song import Song, SongCreate, SongUpdate
from src.models.user import User
from src.routers.songs import (
    create_song,
    delete_song,
    get_song,
    get_songs,
    update_song,
)


def test_create_song_only_adds_to_explicitly_requested_setlists(
    session: Session,
) -> None:
    user = User(email="user@example.com", display_name="User", password="secret")
    session.add(user)
    session.flush()

    library = Setlist(user_id=user.id, name="Library", is_library=True)
    session.add(library)
    session.commit()

    created = create_song(
        song_data=SongCreate(
            title="Song",
            artist="Artist",
            setlist_ids=[],
        ),
        background_tasks=BackgroundTasks(),
        session=session,
        current_user=user,
    )

    entries = session.exec(select(SetlistEntry).where(SetlistEntry.song_id == created.id)).all()
    assert entries == []


def test_get_songs_returns_all_songs(session: Session) -> None:
    song_a = Song(title="A", artist="Artist")
    song_b = Song(title="B", artist="Artist")
    session.add_all([song_a, song_b])
    session.commit()

    songs = get_songs(session)

    assert len(songs) == 2
    assert {song.title for song in songs} == {"A", "B"}


def test_get_song_returns_song_by_id(session: Session) -> None:
    user = User(email="viewer3@example.com", display_name="Viewer3", password="secret")
    song = Song(title="Song", artist="Artist")
    session.add_all([user, song])
    session.commit()

    result = get_song(song.id, session, user)

    assert result.id == song.id


def test_update_song_adds_and_removes_setlist_entries(session: Session) -> None:
    user = User(email="user6@example.com", display_name="User6", password="secret")
    session.add(user)
    session.flush()

    setlist_a = Setlist(user_id=user.id, name="A")
    setlist_b = Setlist(user_id=user.id, name="B")
    session.add_all([setlist_a, setlist_b])
    session.flush()

    song = Song(title="Song", artist="Artist")
    session.add(song)
    session.flush()
    session.add(SetlistEntry(setlist_id=setlist_a.id, song_id=song.id, position=1))
    session.commit()

    updated = update_song(
        song.id,
        SongUpdate(
            setlist_ids_to_add=[setlist_b.id],
            setlist_ids_to_remove=[setlist_a.id],
        ),
        session,
        user,
    )

    assert updated.id == song.id
    assert session.get(SetlistEntry, (setlist_a.id, song.id)) is None
    assert session.get(SetlistEntry, (setlist_b.id, song.id)) is not None


def test_delete_song_deletes_globally_when_no_remaining_entries(
    session: Session,
) -> None:
    user = User(email="deleter@example.com", display_name="Deleter", password="secret")
    session.add(user)
    session.flush()

    setlist = Setlist(user_id=user.id, name="D Setlist")
    session.add(setlist)
    session.flush()

    song = Song(title="Song", artist="Artist")
    session.add(song)
    session.flush()

    session.add(SetlistEntry(setlist_id=setlist.id, song_id=song.id, position=1))
    session.commit()

    delete_song(song.id, session, user)

    assert session.get(SetlistEntry, (setlist.id, song.id)) is None
    assert session.get(Song, song.id) is None


def test_delete_song_keeps_song_if_other_user_has_entry(session: Session) -> None:
    user1 = User(email="u1@example.com", display_name="U1", password="secret")
    user2 = User(email="u2@example.com", display_name="U2", password="secret")
    session.add_all([user1, user2])
    session.flush()

    s1 = Setlist(user_id=user1.id, name="S1")
    s2 = Setlist(user_id=user2.id, name="S2")
    session.add_all([s1, s2])
    session.flush()

    song = Song(title="Song", artist="Artist")
    session.add(song)
    session.flush()

    session.add_all(
        [
            SetlistEntry(setlist_id=s1.id, song_id=song.id, position=1),
            SetlistEntry(setlist_id=s2.id, song_id=song.id, position=1),
        ]
    )
    session.commit()

    delete_song(song.id, session, user1)

    assert session.get(SetlistEntry, (s1.id, song.id)) is None
    assert session.get(SetlistEntry, (s2.id, song.id)) is not None
    assert session.get(Song, song.id) is not None
