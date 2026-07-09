"""Song router definitions for the Setlist API.

Provides CRUD endpoints for song resources using FastAPI and SQLModel.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlmodel import Session, select

from src.core.dependencies import get_current_user
from src.database import get_session
from src.models.setlist import Setlist, SetlistEntry
from src.models.song import Song, SongCreate, SongRead, SongUpdate
from src.models.user import User

router = APIRouter()


def get_next_position(setlist_id: UUID, session: Session) -> int:
    """Return the next available position in a setlist."""
    statement = (
        select(SetlistEntry)
        .where(SetlistEntry.setlist_id == setlist_id)
        .order_by(desc(SetlistEntry.position))
    )
    last_entry = session.exec(statement).first()
    return (last_entry.position + 1) if last_entry else 1


def add_song_to_setlist(
    song_id: UUID,
    setlist_id: UUID,
    session: Session,
) -> None:
    """Add a song to a setlist if it is not already present."""
    existing = session.get(SetlistEntry, (setlist_id, song_id))
    if not existing:
        entry = SetlistEntry(
            setlist_id=setlist_id,
            song_id=song_id,
            position=get_next_position(setlist_id, session),
        )
        session.add(entry)


def user_has_song_access(song_id: UUID, user_id: UUID, session: Session) -> bool:
    """Return whether the user currently has the song in one of their setlists."""
    user_setlist_ids = session.exec(
        select(Setlist.id).where(Setlist.user_id == user_id)
    ).all()
    if not user_setlist_ids:
        return False

    statement = select(SetlistEntry).where(
        SetlistEntry.song_id == song_id,
        SetlistEntry.setlist_id.in_(user_setlist_ids),
    )
    return session.exec(statement).first() is not None


def validate_user_setlist_ids(
    setlist_ids: list[UUID],
    user_id: UUID,
    session: Session,
) -> None:
    """
    Verify that all provided setlist IDs exist and belong to the user.

    Raises HTTP 403 if any setlist is not owned by the user.
    Raises HTTP 404 if any setlist does not exist.
    """
    for setlist_id in setlist_ids:
        setlist = session.get(Setlist, setlist_id)
        if not setlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setlist {setlist_id} not found",
            )
        if setlist.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to access setlist {setlist_id}",
            )


@router.get("/", response_model=list[SongRead])
def get_songs(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Song]:
    """Return all songs in the global songs table."""
    return list(session.exec(select(Song)).all())


@router.post("/", response_model=SongRead, status_code=status.HTTP_201_CREATED)
def create_song(
    song_data: SongCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Song:
    """
    Save a song to one or more of the user's setlists.

    If a song with the same mbid already exists in the global songs table,
    it is reused rather than duplicated.
    """
    setlist_ids = song_data.setlist_ids
    validate_user_setlist_ids(setlist_ids, current_user.id, session)

    song = session.exec(
        select(Song).where(Song.mbid == song_data.mbid)
    ).first()

    if not song:
        song = Song(
            mbid=song_data.mbid,
            title=song_data.title,
            artist=song_data.artist,
            duration_ms=song_data.duration_ms,
            album=song_data.album,
            release_year=song_data.release_year,
        )
        session.add(song)
        session.flush()

    for setlist_id in setlist_ids:
        add_song_to_setlist(song.id, setlist_id, session)

    session.commit()
    session.refresh(song)
    return song


@router.get("/{song_id}", response_model=SongRead)
def get_song(
    song_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Song:
    """Return a single song by ID."""
    song = session.get(Song, song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found",
        )
    return song


@router.patch("/{song_id}", response_model=SongRead)
def update_song(
    song_id: UUID,
    song_data: SongUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Song:
    """
    Update a song's mutable fields and/or its setlist memberships.

    - album and release_year can be updated directly.
    - setlist_ids_to_add adds the song to additional setlists.
    - setlist_ids_to_remove removes the song from specified setlists.
    """
    song = session.get(Song, song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found",
        )

    if not user_has_song_access(song.id, current_user.id, session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to manage this song",
        )

    update_data = song_data.model_dump(
        exclude_unset=True,
        exclude={"setlist_ids_to_add", "setlist_ids_to_remove"},
    )
    if update_data:
        song.sqlmodel_update(update_data)
        session.add(song)

    if song_data.setlist_ids_to_add:
        validate_user_setlist_ids(
            song_data.setlist_ids_to_add, current_user.id, session
        )
        for setlist_id in song_data.setlist_ids_to_add:
            add_song_to_setlist(song.id, setlist_id, session)

    if song_data.setlist_ids_to_remove:
        validate_user_setlist_ids(
            song_data.setlist_ids_to_remove, current_user.id, session
        )
        for setlist_id in song_data.setlist_ids_to_remove:
            entry = session.get(SetlistEntry, (setlist_id, song.id))
            if entry:
                session.delete(entry)

    session.commit()
    session.refresh(song)
    return song


@router.delete("/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_song(
    song_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    Remove a song from all of the current user's setlists.

    If no other user has this song in any setlist, the song is also
    deleted from the global songs table.
    Raises HTTP 404 if the song does not exist.
    """
    song = session.get(Song, song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found",
        )

    if not user_has_song_access(song.id, current_user.id, session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to manage this song",
        )

    user_setlist_ids = session.exec(
        select(Setlist.id).where(Setlist.user_id == current_user.id)
    ).all()

    for setlist_id in user_setlist_ids:
        entry = session.get(SetlistEntry, (setlist_id, song_id))
        if entry:
            session.delete(entry)

    session.flush()

    remaining = session.exec(
        select(SetlistEntry).where(SetlistEntry.song_id == song_id)
    ).first()

    if not remaining:
        session.delete(song)

    session.commit()