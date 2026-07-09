"""Song domain models and request/response schemas."""

from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class SongBase(SQLModel):
    """Shared song fields used by create and read models."""

    mbid: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=1, max_length=255)
    artist: str = Field(min_length=1, max_length=255)
    duration_ms: int | None = Field(default=None)
    album: str | None = Field(default=None, max_length=255)
    release_year: int | None = Field(default=None)


class Song(SongBase, table=True):
    """Database model representing a song in the global songs table."""

    __tablename__ = "songs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class SongCreate(SongBase):
    """Request schema for saving a new song."""

    pass


class SongRead(SongBase):
    """Response schema returned for song resources."""

    id: UUID


class SongUpdate(SQLModel):
    """Request schema for updating a song."""

    album: str | None = Field(default=None, max_length=255)
    release_year: int | None = Field(default=None)
