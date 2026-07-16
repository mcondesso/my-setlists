"""Song link domain models mapping songs to external platform URLs."""

from enum import StrEnum
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from src.models.song import Song


class Platform(StrEnum):
    """Supported music platforms for song links."""

    DISCOGS = "discogs"
    YOUTUBE = "youtube"
    SPOTIFY = "spotify"
    APPLE_MUSIC = "apple_music"
    BANDCAMP = "bandcamp"


class SongLink(SQLModel, table=True):
    """Database model representing a song's presence on an external platform."""

    __tablename__ = "song_links"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    song_id: UUID = Field(foreign_key="songs.id", ondelete="CASCADE")
    platform: Platform
    external_id: str = Field(max_length=255)
    url: str | None = Field(max_length=512)

    song: Mapped[Optional["Song"]] = Relationship(back_populates="links")


class SongLinkCreate(SQLModel):
    """Request schema for adding a new platform link to a song."""

    external_id: str = Field(max_length=255)
    url: str | None = Field(default=None, max_length=512)


class SongLinkUpdate(SQLModel):
    """Request schema for updating an existing platform link."""

    external_id: str | None = Field(default=None, max_length=255)
    url: str | None = Field(default=None, max_length=512)


class SongLinkRead(SQLModel):
    """Response schema returned for song link resources."""

    id: UUID
    song_id: UUID
    platform: Platform
    external_id: str
    url: str


class SongLinkReadNested(SQLModel):
    """Response schema for a song link nested inside a song response."""

    platform: Platform
    external_id: str
    url: str
