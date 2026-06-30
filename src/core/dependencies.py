"""FastAPI dependencies for authentication and session management."""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from src.core.security import decode_token
from src.database import get_session
from src.models.user import User
from src.core.security import verify_password

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def authenticate_user(
    session: Annotated[Session, Depends(get_session)], email: str, password: str
) -> User | None:
    """
    Verify a user's credentials against the database.

    Returns the matching User if the email exists and the password is
    correct, otherwise returns None.
    """

    sql_query = select(User).where(User.email == email)
    user = session.exec(sql_query).first()
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user
