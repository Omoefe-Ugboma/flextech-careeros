
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError

from app.core.database import settings


ALGORITHM = "HS256"


def create_access_token(user_id: int) -> str:
    """
    Create a signed JWT access token for an authenticated user.
    """

    now = datetime.now(timezone.utc)

    expires_at = now + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expires_at,
        "type": "access",
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """
    Verify and decode an access token.

    Raises InvalidTokenError if the token is invalid,
    expired, incorrectly signed, or not an access token.
    """

    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[ALGORITHM],
        options={
            "require": ["sub", "iat", "exp"],
        },
    )

    if payload.get("type") != "access":
        raise InvalidTokenError("Invalid token type.")

    return payload
