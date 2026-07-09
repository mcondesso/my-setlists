"""User domain models and request/response schemas."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from pydantic import EmailStr
from sqlalchemy import func, Column, DateTime
from sqlalchemy.orm import Mapped
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from src.models.setlist import Setlist


class UserBase(SQLModel):
    """Shared user fields used by create and read models."""

    email: EmailStr = Field(max_length=255)
    display_name: str = Field(max_length=255)


class User(UserBase, table=True):
    """Database model representing a stored user account."""

    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: EmailStr = Field(max_length=255, unique=True, index=True)
    display_name: str = Field(max_length=255, min_length=1)
    password: str = Field(max_length=255)
    created_at: datetime = Field(
        default=None, sa_column=Column(DateTime(), server_default=func.now())
    )

    # Relationships
    setlists: Mapped[list["Setlist"]] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class UserCreate(UserBase):
    """Request schema for creating a new user."""

    password: str = Field(min_length=8)


class UserRead(UserBase):
    """Response schema returned for user resources."""

    id: UUID
    created_at: datetime


class UserUpdate(SQLModel):
    """Request schema for updating a user's display name."""

    display_name: str = Field(max_length=255, min_length=1)
