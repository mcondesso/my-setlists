"""Song domain models and request/response schemas."""

from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4


class SongBase(SQLModel):
    """Shared song fields used by create and read models."""

    mbid: str = Field(max_length=36)
    title: str = Field(max_length=255)
    artist: str = Field(max_length=255)
    duration_ms: int | None = None
    album: str | None = None
    release_year: int | None = None


class Song(SongBase, table=True):
    """Database model representing a stored song."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    mbid: str = Field(max_length=36, unique=True)
    title: str = Field(max_length=255, min_length=1)
    artist: str = Field(max_length=255, min_length=1)


class SongCreate(SongBase):
    """Request schema for creating a new song."""

    pass


class SongRead(SongBase):
    """Response schema returned for song resources."""

    id: UUID


class SongUpdate(SQLModel):
    """Request schema for updating a song."""

    album: str | None = None
    release_year: int | None = None
