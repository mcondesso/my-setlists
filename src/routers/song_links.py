"""Song link routes: manage platform links for songs."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from src.core.dependencies import get_current_user
from src.database import get_session
from src.models.song import Song
from src.models.song_link import (
    Platform,
    SongLink,
    SongLinkCreate,
    SongLinkReadNested,
    SongLinkUpdate,
)
from src.models.user import User

router = APIRouter()


def get_song_or_404(song_id: UUID, session: Session) -> Song:
    """Fetch a song by ID or raise HTTP 404."""
    song = session.get(Song, song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found",
        )
    return song


def get_song_link_or_404(song_id: UUID, platform: Platform, session: Session) -> SongLink:
    """Fetch a song link by song ID and platform or raise HTTP 404."""
    link = session.exec(
        select(SongLink).where(
            SongLink.song_id == song_id,
            SongLink.platform == platform,
        )
    ).first()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {platform.value} link found for this song",
        )
    return link


@router.get("/", response_model=list[SongLinkReadNested])
def get_song_links(
    song_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[SongLink]:
    """Return all platform links for a song."""
    get_song_or_404(song_id, session)
    return list(session.exec(select(SongLink).where(SongLink.song_id == song_id)).all())


@router.post("/{platform}", response_model=SongLinkReadNested, status_code=status.HTTP_201_CREATED)
def add_song_link(
    song_id: UUID,
    platform: Platform,
    link_data: SongLinkCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SongLink:
    """
    Add a new platform link to a song.

    Raises HTTP 400 if a link for this platform already exists for the song.
    """
    get_song_or_404(song_id, session)

    existing = session.exec(
        select(SongLink).where(
            SongLink.song_id == song_id,
            SongLink.platform == platform,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A {platform.value} link already exists for this song — use PUT to update it",
        )

    link = SongLink(
        song_id=song_id,
        platform=platform,
        external_id=link_data.external_id,
        url=link_data.url,
    )
    session.add(link)
    session.commit()
    session.refresh(link)
    return link


@router.put("/{platform}", response_model=SongLinkReadNested)
def update_song_link(
    song_id: UUID,
    platform: Platform,
    link_data: SongLinkUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SongLink:
    """
    Update the external ID and/or URL for an existing platform link.

    Raises HTTP 404 if no link exists for this platform.
    """
    get_song_or_404(song_id, session)
    link = get_song_link_or_404(song_id, platform, session)

    update_data = link_data.model_dump(exclude_unset=True)
    link.sqlmodel_update(update_data)
    session.add(link)
    session.commit()
    session.refresh(link)
    return link


@router.delete("/{platform}", status_code=status.HTTP_204_NO_CONTENT)
def delete_song_link(
    song_id: UUID,
    platform: Platform,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    Remove a platform link from a song.

    Raises HTTP 404 if no link exists for this platform.
    """
    get_song_or_404(song_id, session)
    link = get_song_link_or_404(song_id, platform, session)
    session.delete(link)
    session.commit()
