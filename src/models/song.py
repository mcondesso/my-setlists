"""Song domain models and request/response schemas."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from src.models.setlist import SetlistEntry


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

    # Relationships
    entries: Mapped[list["SetlistEntry"]] = Relationship(
        back_populates="song",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class SongCreate(SongBase):
    """Request schema for saving a new song."""

    setlist_ids: list[UUID] = Field(default_factory=list)


class SongRead(SongBase):
    """Response schema returned for song resources."""

    id: UUID


class SongUpdate(SQLModel):
    """Request schema for updating a song's mutable fields."""

    album: str | None = Field(default=None, max_length=255)
    release_year: int | None = Field(default=None)
    setlist_ids_to_add: list[UUID] = Field(default_factory=list)
    setlist_ids_to_remove: list[UUID] = Field(default_factory=list)
