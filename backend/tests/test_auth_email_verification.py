
from datetime import datetime, timedelta, timezone

import pytest

from app.models.user import User
from app.models.email_verification_token import EmailVerificationToken
from app.services.auth.email_verification import (
    create_verification_token,
    hash_verification_token,
    verify_email,
    InvalidVerificationTokenError,
)


def create_test_user(test_db):
    user = User(
        email="verify@example.com",
        hashed_password="test-password-hash",
        is_active=True,
        is_verified=False,
    )

    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    return user


def test_create_verification_token(test_db):
    user = create_test_user(test_db)

    raw_token = create_verification_token(test_db, user.id)
    test_db.commit()

    assert isinstance(raw_token, str)
    assert len(raw_token) > 0

    stored_token = test_db.query(
        EmailVerificationToken
    ).filter_by(
        token_hash=hash_verification_token(raw_token)
    ).first()

    assert stored_token is not None
    assert stored_token.user_id == user.id
    assert raw_token != stored_token.token_hash


def test_verify_email_successfully(test_db):
    user = create_test_user(test_db)

    raw_token = create_verification_token(test_db, user.id)
    test_db.commit()

    verified_user = verify_email(test_db, raw_token)

    assert verified_user.is_verified is True


def test_verification_token_cannot_be_reused(test_db):
    user = create_test_user(test_db)

    raw_token = create_verification_token(test_db, user.id)
    test_db.commit()

    verify_email(test_db, raw_token)

    with pytest.raises(InvalidVerificationTokenError):
        verify_email(test_db, raw_token)


def test_unknown_verification_token_is_rejected(test_db):
    with pytest.raises(InvalidVerificationTokenError):
        verify_email(test_db, "unknown-verification-token")


def test_expired_verification_token_is_rejected(test_db):
    user = create_test_user(test_db)

    raw_token = "expired-verification-token"

    token_record = EmailVerificationToken(
        user_id=user.id,
        token_hash=hash_verification_token(raw_token),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )

    test_db.add(token_record)
    test_db.commit()

    with pytest.raises(InvalidVerificationTokenError):
        verify_email(test_db, raw_token)


def test_verification_token_is_marked_as_used(test_db):
    user = create_test_user(test_db)

    raw_token = create_verification_token(test_db, user.id)
    test_db.commit()

    verify_email(test_db, raw_token)

    token_record = test_db.query(
        EmailVerificationToken
    ).filter_by(
        token_hash=hash_verification_token(raw_token)
    ).first()

    assert token_record.used_at is not None