"""Setlist and SetlistEntry domain models and request/response schemas."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from pydantic import ConfigDict
from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from src.models.song import SongReadWithLinks

if TYPE_CHECKING:
    from src.models.song import Song, SongReadWithLinks
    from src.models.user import User


class SetlistBase(SQLModel):
    """Shared setlist fields used by create and read models."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    is_public: bool = Field(default=False)


class Setlist(SetlistBase, table=True):
    """Database model representing a stored setlist."""

    __tablename__ = "setlists"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    is_library: bool = Field(default=False)
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(), server_default=func.now()),
    )

    entries: Mapped[list["SetlistEntry"]] = Relationship(
        back_populates="setlist",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    user: Mapped[Optional["User"]] = Relationship(back_populates="setlists")


class SetlistCreate(SQLModel):
    """Request schema for creating a new setlist."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    is_public: bool = Field(default=False)


class SetlistRead(SetlistBase):
    """Response schema returned for setlist resources."""

    id: UUID
    owner_display_name: str
    is_library: bool
    created_at: datetime

    @classmethod
    def from_orm(cls, setlist: "Setlist") -> "SetlistRead":
        """Build a SetlistRead from a Setlist ORM object."""
        return cls(
            id=setlist.id,
            name=setlist.name,
            description=setlist.description,
            is_public=setlist.is_public,
            is_library=setlist.is_library,
            created_at=setlist.created_at,
            owner_display_name=setlist.user.display_name,
        )


class SetlistUpdate(SQLModel):
    """Request schema for updating a setlist's mutable fields."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    is_public: bool | None = Field(default=None)


class SetlistEntry(SQLModel, table=True):
    """Database model representing a song's membership in a setlist."""

    __tablename__ = "setlist_entries"

    setlist_id: UUID = Field(foreign_key="setlists.id", primary_key=True, ondelete="CASCADE")
    song_id: UUID = Field(foreign_key="songs.id", primary_key=True, ondelete="CASCADE")
    position: int
    added_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(), server_default=func.now()),
    )

    setlist: Mapped[Optional["Setlist"]] = Relationship(back_populates="entries")
    song: Mapped[Optional["Song"]] = Relationship(back_populates="entries")


class SetlistEntryRead(SQLModel):
    """Response schema returned for setlist entry resources."""

    setlist_id: UUID
    song_id: UUID
    position: int
    added_at: datetime


class SetlistEntryReadWithSong(SQLModel):
    """Response schema for a setlist entry with full song details."""

    model_config = ConfigDict(from_attributes=True)

    setlist_id: UUID
    song_id: UUID
    position: int
    added_at: datetime
    song: SongReadWithLinks


class SetlistReadWithEntries(SQLModel):
    """Response schema for a setlist including all its song entries."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_display_name: str
    name: str
    description: str | None
    is_library: bool
    is_public: bool
    created_at: datetime
    entries: list[SetlistEntryReadWithSong] = []

    @classmethod
    def from_orm(cls, setlist: "Setlist") -> "SetlistReadWithEntries":
        """Build a SetlistReadWithEntries from a Setlist ORM object."""
        return cls(
            id=setlist.id,
            name=setlist.name,
            description=setlist.description,
            is_public=setlist.is_public,
            is_library=setlist.is_library,
            created_at=setlist.created_at,
            owner_display_name=setlist.user.display_name,
            entries=setlist.entries,
        )
