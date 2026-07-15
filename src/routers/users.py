"""User profile routes: read, update, and delete the current account."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from src.core.dependencies import get_current_user
from src.database import get_session
from src.models.user import User, UserRead, UserReadWithSetlists, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserReadWithSetlists)
def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Return the profile of the currently authenticated user."""
    return current_user


@router.patch("/me", response_model=UserRead)
def update_current_user(
    user_data: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    """Update the display name of the currently authenticated user."""
    current_user.display_name = user_data.display_name
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> None:
    """Delete the currently authenticated user's account and all owned setlists."""
    session.delete(current_user)
    session.commit()
