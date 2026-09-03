from uuid import UUID

from pydantic import BaseModel


class Token(BaseModel):
    """Response schema returned after a successful login."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Schema for the data extracted from a decoded JWT payload."""

    user_id: UUID
