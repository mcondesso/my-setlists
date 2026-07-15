"""Setlist and SetlistEntry domain models and request/response schemas."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from src.models.song import Song
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
    user_id: UUID = Field(foreign_key="users.id")
    is_library: bool = Field(default=False)
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(), server_default=func.now()),
    )

    # Relationships
    entries: Mapped[list["SetlistEntry"]] = Relationship(
        back_populates="setlist",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
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
    user_id: UUID
    is_library: bool
    created_at: datetime


class SetlistUpdate(SQLModel):
    """Request schema for updating a setlist's mutable fields."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    is_public: bool | None = Field(default=None)


class SetlistEntry(SQLModel, table=True):
    """Database model representing a song's membership in a setlist."""

    __tablename__ = "setlist_entries"

    setlist_id: UUID = Field(foreign_key="setlists.id", primary_key=True)
    song_id: UUID = Field(foreign_key="songs.id", primary_key=True)
    position: int
    added_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(), server_default=func.now()),
    )

    # Relationships
    setlist: Mapped[Optional["Setlist"]] = Relationship(back_populates="entries")
    song: Mapped[Optional["Song"]] = Relationship(back_populates="entries")


class SetlistEntryRead(SQLModel):
    """Response schema returned for setlist entry resources."""

    setlist_id: UUID
    song_id: UUID
    position: int
    added_at: datetime
