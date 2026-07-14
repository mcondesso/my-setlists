"""User route tests covering profile read, update, and deletion behavior."""

from sqlmodel import Session

from src.models.setlist import Setlist, SetlistEntry
from src.models.song import Song
from src.models.user import User
from src.routers.users import (
    delete_current_user,
    read_current_user,
    update_current_user,
)


def test_read_current_user_returns_profile(session: Session) -> None:
    user = User(email="reader@example.com", display_name="Reader", password="secret")
    session.add(user)
    session.commit()

    result = read_current_user(user)

    assert result.id == user.id
    assert result.email == "reader@example.com"


def test_update_current_user_changes_display_name(session: Session) -> None:
    user = User(email="updater@example.com", display_name="Updater", password="secret")
    session.add(user)
    session.commit()

    updated = update_current_user(
        user_data=type("U", (), {"display_name": "Updated"})(),
        current_user=user,
        session=session,
    )

    assert updated.display_name == "Updated"
    assert session.get(User, user.id).display_name == "Updated"


def test_delete_current_user_cascades_setlists_and_entries(session: Session) -> None:
    user = User(email="owner2@example.com", display_name="Owner2", password="secret")
    session.add(user)
    session.flush()

    setlist = Setlist(user_id=user.id, name="Owner2 Setlist")
    song = Song(mbid="mbid-4", title="Song", artist="Artist")
    session.add_all([setlist, song])
    session.flush()
    session.add(SetlistEntry(setlist_id=setlist.id, song_id=song.id, position=1))
    session.commit()

    delete_current_user(user, session)

    assert session.get(User, user.id) is None
    assert session.get(Setlist, setlist.id) is None
    assert session.get(SetlistEntry, (setlist.id, song.id)) is None
    assert session.get(Song, song.id) is not None
