
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from jwt.exceptions import InvalidTokenError

from app.core.database import settings
from app.services.auth.token import (
    ALGORITHM,
    create_access_token,
    decode_access_token,
)


def test_create_access_token():
    token = create_access_token(user_id=1)

    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_valid_access_token():
    token = create_access_token(user_id=25)

    payload = decode_access_token(token)

    assert payload["sub"] == "25"
    assert payload["type"] == "access"


def test_reject_expired_access_token():
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=5)

    token = jwt.encode(
        {
            "sub": "25",
            "iat": expired_time - timedelta(minutes=5),
            "exp": expired_time,
            "type": "access",
        },
        settings.JWT_SECRET_KEY,
        algorithm=ALGORITHM,
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_reject_token_with_wrong_secret():
    token = jwt.encode(
        {
            "sub": "25",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            "type": "access",
        },
        "incorrect-test-secret-that-is-at-least-32-bytes",
        algorithm=ALGORITHM,
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_reject_refresh_token_as_access_token():
    token = jwt.encode(
        {
            "sub": "25",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            "type": "refresh",
        },
        settings.JWT_SECRET_KEY,
        algorithm=ALGORITHM,
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)
