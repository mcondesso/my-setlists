"""Song link domain models mapping songs to external platform URLs."""

from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from src.models.song import Song


class SongLink(SQLModel, table=True):
    """Database model representing a song's presence on an external platform."""

    __tablename__ = "song_links"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    song_id: UUID = Field(foreign_key="songs.id", ondelete="CASCADE")
    platform: str = Field(max_length=50)
    external_id: str = Field(max_length=255)
    url: str | None = Field(max_length=512)

    song: Mapped[Optional["Song"]] = Relationship(back_populates="links")


class SongLinkRead(SQLModel):
    """Response schema returned for song link resources."""

    id: UUID
    song_id: UUID
    platform: str
    external_id: str
    url: str


class SongLinkReadNested(SQLModel):
    """Response schema for a song link nested inside a song response."""

    platform: str
    external_id: str
    url: str
