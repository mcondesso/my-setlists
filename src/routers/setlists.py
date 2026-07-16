"""Setlist routes: create, read, update, delete, and manage song entries."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlmodel import Session, select

from src.core.dependencies import get_current_user
from src.database import get_session
from src.models.setlist import (
    Setlist,
    SetlistCreate,
    SetlistEntry,
    SetlistEntryRead,
    SetlistEntryReadWithSong,
    SetlistRead,
    SetlistReadWithEntries,
    SetlistUpdate,
)
from src.models.song import Song
from src.models.user import User

router = APIRouter()


def get_user_setlist(
    setlist_id: UUID,
    current_user: User,
    session: Session,
) -> Setlist:
    """
    Fetch a setlist by ID and verify it belongs to the current user.

    Raises HTTP 404 if not found, HTTP 403 if owned by another user.
    """
    setlist = session.get(Setlist, setlist_id)
    if not setlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setlist not found",
        )
    if setlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this setlist",
        )
    return setlist


def get_accessible_setlist(
    setlist_id: UUID,
    current_user: User,
    session: Session,
) -> Setlist:
    """Fetch a setlist if it is public or owned by the current user."""
    setlist = session.get(Setlist, setlist_id)
    if not setlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setlist not found",
        )
    if setlist.is_public or setlist.user_id == current_user.id:
        return setlist

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this setlist",
    )


@router.get("/", response_model=list[SetlistRead])
def get_setlists(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Setlist]:
    """
    Return all setlists visible to the current user.

    Results include the user's own setlists and all public setlists from
    other users. The current user's setlists are returned first.
    """
    statement = (
        select(Setlist)
        .where(
            (Setlist.user_id == current_user.id) | (Setlist.is_public == True)  # noqa: E712
        )
        .order_by(
            (Setlist.user_id == current_user.id).desc(),
            Setlist.created_at.desc(),
        )
    )
    setlists = session.exec(statement).all()
    return [SetlistReadWithEntries.from_orm(s) for s in setlists]


@router.post("/", response_model=SetlistRead, status_code=status.HTTP_201_CREATED)
def create_setlist(
    setlist_data: SetlistCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Setlist:
    """
    Create a new setlist for the current user.

    The is_library flag is always set to False for user-created setlists.
    """
    setlist = Setlist(
        user_id=current_user.id,
        name=setlist_data.name,
        description=setlist_data.description,
        is_public=setlist_data.is_public,
        is_library=False,
    )
    session.add(setlist)
    session.commit()
    session.refresh(setlist)
    return SetlistRead.from_orm(setlist)


@router.get("/{setlist_id}", response_model=SetlistReadWithEntries)
def get_setlist(
    setlist_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Setlist:
    """
    Return a single setlist by ID.

    Public setlists are accessible by any authenticated user.
    Private setlists are only accessible by their owner.
    """
    setlist = session.get(Setlist, setlist_id)
    if not setlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setlist not found",
        )
    if not setlist.is_public and setlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this setlist",
        )
    return SetlistReadWithEntries.from_orm(setlist)


@router.patch("/{setlist_id}", response_model=SetlistRead)
def update_setlist(
    setlist_id: UUID,
    setlist_data: SetlistUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Setlist:
    """
    Update a setlist's name, description, or visibility.

    For library setlists, only is_public can be changed.
    Raises HTTP 403 if attempting to change name or description of the library.
    """
    setlist = get_user_setlist(setlist_id, current_user, session)

    if setlist.is_library and (
        setlist_data.name is not None or setlist_data.description is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The library setlist's name and description cannot be changed",
        )

    setlist_update = setlist_data.model_dump(exclude_unset=True)
    setlist.sqlmodel_update(setlist_update)
    session.add(setlist)
    session.commit()
    session.refresh(setlist)
    return setlist


@router.delete("/{setlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_setlist(
    setlist_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    Delete a setlist and all its entries.

    Raises HTTP 403 if the setlist is the user's library.
    """
    setlist = get_user_setlist(setlist_id, current_user, session)

    if setlist.is_library:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The library setlist cannot be deleted",
        )
    session.delete(setlist)
    session.commit()


@router.get("/{setlist_id}/songs", response_model=list[SetlistEntryReadWithSong])
def get_setlist_songs(
    setlist_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[SetlistEntry]:
    """Return all song entries in a setlist, ordered by position."""
    setlist = get_accessible_setlist(setlist_id, current_user, session)
    statement = (
        select(SetlistEntry)
        .where(SetlistEntry.setlist_id == setlist.id)
        .order_by(desc(SetlistEntry.position))
    )
    return list(session.exec(statement).all())


@router.post(
    "/{setlist_id}/songs/{song_id}",
    response_model=SetlistEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def add_song_to_setlist(
    setlist_id: UUID,
    song_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SetlistEntry:
    """
    Add a song to a setlist.

    The song is appended at the end of the setlist.
    Raises HTTP 404 if the song does not exist.
    Raises HTTP 400 if the song is already in the setlist.
    """
    setlist = get_user_setlist(setlist_id, current_user, session)

    song = session.get(Song, song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found",
        )

    existing_entry = session.get(SetlistEntry, (setlist.id, song_id))
    if existing_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Song already exists in this setlist",
        )

    statement = (
        select(SetlistEntry)
        .where(SetlistEntry.setlist_id == setlist.id)
        .order_by(desc(SetlistEntry.position))
    )
    last_entry = session.exec(statement).first()
    next_position = (last_entry.position + 1) if last_entry else 1

    entry = SetlistEntry(
        setlist_id=setlist.id,
        song_id=song_id,
        position=next_position,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


@router.delete(
    "/{setlist_id}/songs/{song_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_song_from_setlist(
    setlist_id: UUID,
    song_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    Remove a song from a setlist.

    This only removes the connection between the setlist and the song.
    The shared song record remains in the catalog for public browsing.
    Raises HTTP 404 if the entry does not exist.
    """
    setlist = get_user_setlist(setlist_id, current_user, session)

    entry = session.get(SetlistEntry, (setlist.id, song_id))
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found in this setlist",
        )

    session.delete(entry)
    session.commit()
