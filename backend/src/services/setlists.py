"""Domain helpers for manipulating setlist entries."""

from uuid import UUID

from sqlalchemy import desc
from sqlmodel import Session, select

from src.models.setlist import SetlistEntry


def get_next_position(setlist_id: UUID, session: Session) -> int:
    """Return the position to assign to the next song appended to a setlist."""
    statement = (
        select(SetlistEntry)
        .where(SetlistEntry.setlist_id == setlist_id)
        .order_by(desc(SetlistEntry.position))
    )
    last_entry = session.exec(statement).first()
    return (last_entry.position + 1) if last_entry else 1


def add_song_to_setlist(song_id: UUID, setlist_id: UUID, session: Session) -> None:
    """Append a song to a setlist if it is not already present. Does not commit."""
    if session.get(SetlistEntry, (setlist_id, song_id)) is not None:
        return
    session.add(
        SetlistEntry(
            setlist_id=setlist_id,
            song_id=song_id,
            position=get_next_position(setlist_id, session),
        )
    )
