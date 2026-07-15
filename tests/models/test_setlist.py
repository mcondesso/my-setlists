"""Setlist route tests covering create, read, update, and delete flows."""

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from src.models.setlist import Setlist, SetlistCreate, SetlistEntry, SetlistUpdate
from src.models.song import Song
from src.models.user import User
from src.routers.setlists import (
    add_song_to_setlist,
    create_setlist,
    delete_setlist,
    get_setlist,
    get_setlist_songs,
    get_setlists,
    remove_song_from_setlist,
    update_setlist,
)


def test_create_setlist_saves_new_setlist(session: Session) -> None:
    user = User(email="user@example.com", display_name="User", password="secret")
    session.add(user)
    session.flush()

    created = create_setlist(
        setlist_data=SetlistCreate(
            name="My Setlist",
            description="A test setlist",
            is_public=False,
        ),
        session=session,
        current_user=user,
    )

    assert created.user_id == user.id
    assert created.is_library is False
    assert session.get(Setlist, created.id) is not None


def test_get_setlists_returns_only_owned_setlists(session: Session) -> None:
    owner = User(email="owner@example.com", display_name="Owner", password="secret")
    other = User(email="other@example.com", display_name="Other", password="secret")
    session.add_all([owner, other])
    session.flush()

    owned = Setlist(user_id=owner.id, name="Owned")
    foreign = Setlist(user_id=other.id, name="Foreign")
    session.add_all([owned, foreign])
    session.commit()

    setlists = get_setlists(session, owner)

    assert len(setlists) == 1
    assert setlists[0].user_id == owner.id
    assert setlists[0].id == owned.id


def test_get_setlist_songs_allows_public_setlist_access(session: Session) -> None:
    owner = User(email="owner2@example.com", display_name="Owner2", password="secret")
    viewer = User(email="viewer@example.com", display_name="Viewer", password="secret")
    session.add_all([owner, viewer])
    session.flush()

    setlist = Setlist(user_id=owner.id, name="Public", is_public=True)
    session.add(setlist)
    session.flush()

    song = Song(title="Song", artist="Artist")
    session.add(song)
    session.flush()

    session.add(SetlistEntry(setlist_id=setlist.id, song_id=song.id, position=1))
    session.commit()

    entries = get_setlist_songs(setlist.id, session, viewer)

    assert len(entries) == 1
    assert entries[0].song_id == song.id


def test_get_setlist_restricts_private_access_to_owner(session: Session) -> None:
    owner = User(email="owner3@example.com", display_name="Owner3", password="secret")
    viewer = User(email="viewer3@example.com", display_name="Viewer3", password="secret")
    session.add_all([owner, viewer])
    session.flush()

    setlist = Setlist(user_id=owner.id, name="Private Setlist", is_public=False)
    session.add(setlist)
    session.commit()

    with pytest.raises(HTTPException) as exc_info:
        get_setlist(setlist.id, session, viewer)

    assert exc_info.value.status_code == 403


def test_update_setlist_rejects_library_name_change(session: Session) -> None:
    user = User(email="user3@example.com", display_name="User3", password="secret")
    session.add(user)
    session.flush()

    library = Setlist(user_id=user.id, name="Library", is_library=True)
    session.add(library)
    session.commit()

    with pytest.raises(HTTPException) as exc_info:
        update_setlist(
            library.id,
            SetlistUpdate(name="New Name", description="New Desc"),
            session,
            user,
        )

    assert exc_info.value.status_code == 403


def test_add_and_remove_song_from_setlist(session: Session) -> None:
    user = User(email="user4@example.com", display_name="User4", password="secret")
    session.add(user)
    session.flush()

    setlist = Setlist(user_id=user.id, name="My Setlist")
    song = Song(title="Song", artist="Artist")
    session.add_all([setlist, song])
    session.commit()

    add_song_to_setlist(setlist.id, song.id, session, user)
    session.commit()

    entries = get_setlist_songs(setlist.id, session, user)
    assert len(entries) == 1

    remove_song_from_setlist(setlist.id, song.id, session, user)
    assert session.get(SetlistEntry, (setlist.id, song.id)) is None


def test_delete_setlist_removes_all_entries(session: Session) -> None:
    user = User(email="user5@example.com", display_name="User5", password="secret")
    session.add(user)
    session.flush()

    setlist = Setlist(user_id=user.id, name="My Setlist")
    song = Song(title="Song", artist="Artist")
    session.add_all([setlist, song])
    session.flush()
    session.add(SetlistEntry(setlist_id=setlist.id, song_id=song.id, position=1))
    session.commit()

    delete_setlist(setlist.id, session, user)

    assert session.get(Setlist, setlist.id) is None
    assert session.get(SetlistEntry, (setlist.id, song.id)) is None
