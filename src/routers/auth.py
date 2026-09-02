"""Authentication routes: registration and login."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.core.dependencies import authenticate_user
from src.core.rate_limit import LOGIN_RATE_LIMIT, limiter
from src.core.security import create_token, hash_password
from src.database import get_session
from src.models.setlist import Setlist
from src.models.token import Token
from src.models.user import User, UserCreate, UserRead

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserCreate,
    session: Annotated[Session, Depends(get_session)],
) -> User:
    """
    Create a new user account and their library setlist.

    Raises HTTP 400 if the email is already registered.
    """
    email_taken = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Email already registered",
    )

    statement = select(User).where(User.email == user_data.email)
    if session.exec(statement).first():
        raise email_taken

    user = User(
        email=user_data.email,
        display_name=user_data.display_name,
        password=hash_password(user_data.password),
    )
    session.add(user)
    session.flush()

    library = Setlist(
        user_id=user.id,
        name="Library",
        is_library=True,
        is_public=False,
    )
    session.add(library)

    try:
        session.commit()
    except IntegrityError as error:
        # Another request registered this email between the check and the commit.
        session.rollback()
        raise email_taken from error

    session.refresh(user)
    return user


@router.post("/login", response_model=Token)
@limiter.limit(LOGIN_RATE_LIMIT)
def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)],
) -> Token:
    """
    Authenticate a user and return a JWT access token.

    Raises HTTP 401 if the email or password is incorrect.
    Raises HTTP 429 once the per-client attempt limit is exceeded.
    """
    user = authenticate_user(session, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_token(user.id)
    return Token(access_token=access_token, token_type="bearer")
