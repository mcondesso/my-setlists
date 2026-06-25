"""Song router definitions for the Setlist API.

Provides CRUD endpoints for song resources using FastAPI and SQLModel.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from uuid import UUID
from src.database import get_session
from src.models.song import Song, SongCreate, SongRead

router = APIRouter()


@router.get("/", response_model=list[SongRead])
def get_songs(session: Session = Depends(get_session)):
    """Return all songs stored in the database."""
    songs = session.exec(select(Song)).all()
    return songs


@router.post("/", response_model=SongRead)
def create_song(song_data: SongCreate, session: Session = Depends(get_session)):
    """Create a new song record from validated request data."""
    song = Song.model_validate(song_data)
    session.add(song)
    session.commit()
    session.refresh(song)
    return song


@router.get("/{song_id}", response_model=SongRead)
def get_song(song_id: UUID, session: Session = Depends(get_session)):
    """Return a single song by its UUID or raise 404 if not found."""
    song = session.get(Song, song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return song


@router.delete("/{song_id}")
def delete_song(song_id: UUID, session: Session = Depends(get_session)):
    """Delete the song with the given UUID from the database."""
    song = session.get(Song, song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    session.delete(song)
    session.commit()
    return {"ok": True}
