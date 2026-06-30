"""Password hashing and JWT creation/verification utilities."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from src.core.config import settings

ALGORITHM = "HS256"

password_hash = PasswordHash.recommended()


def hash_password(plain: str) -> str:
    """Hash a plain text password using the recommended algorithm."""
    return password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain text password against a hashed password."""
    return password_hash.verify(plain, hashed)


def create_token(user_id: UUID) -> str:
    """
    Create a signed JWT containing the user's ID and an expiry timestamp.

    The token expires after the number of minutes defined in settings.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> UUID:
    """
    Decode and verify a JWT, returning the user ID stored in the 'sub' claim.

    Raises jwt.InvalidTokenError if the token is invalid, expired, missing
    the 'sub' claim, or the 'sub' claim is not a valid UUID.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise jwt.InvalidTokenError("Token payload doesn't contain a valid 'sub' claim")

    try:
        return UUID(user_id_str)
    except ValueError:
        raise jwt.InvalidTokenError(f"Invalid UUID in 'sub' claim: {user_id_str}")
