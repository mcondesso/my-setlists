"""Song domain models and request/response schemas."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import ConfigDict
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from src.models.song_link import SongLinkReadNested

if TYPE_CHECKING:
    from src.models.setlist import SetlistEntry
    from src.models.song_link import SongLink, SongLinkReadNested


class SongBase(SQLModel):
    """Shared song fields used by create and read models."""

    title: str = Field(min_length=1, max_length=255)
    artist: str = Field(min_length=1, max_length=255)
    duration_ms: int | None = Field(default=None)
    album: str | None = Field(default=None, max_length=255)
    release_year: int | None = Field(default=None)
    thumbnail: str | None = Field(default=None, max_length=512)


class Song(SongBase, table=True):
    """Database model representing a song in the global songs table."""

    __tablename__ = "songs"
    __table_args__ = (UniqueConstraint("title", "artist"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Relationships
    links: Mapped[list["SongLink"]] = Relationship(
        back_populates="song",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    entries: Mapped[list["SetlistEntry"]] = Relationship(
        back_populates="song",
        sa_relationship_kwargs={"passive_deletes": True},
    )


class SongCreate(SongBase):
    """
    Request schema for saving a new song.

    The song is added to setlists specified in setlist_ids. discogs_id is
    optional but recommended for linking back to the Discogs catalog.
    """

    discogs_id: str | None = Field(default=None, max_length=255)
    discogs_url: str | None = Field(default=None, max_length=512)
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


class SongReadWithLinks(SongBase):
    """Response schema for a song including all its platform links."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    links: list[SongLinkReadNested] = []
