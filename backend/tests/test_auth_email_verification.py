
from datetime import datetime, timedelta, timezone

import pytest

from app.models.user import User
from app.models.email_verification_token import EmailVerificationToken

from app.services.auth.email_verification import (
    create_verification_token,
    hash_verification_token,
    verify_email,
    resend_verification_token,
    InvalidVerificationTokenError,
    VerificationResendCooldownError,
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

def test_resend_verification_token_successfully(test_db):
    user = create_test_user(test_db)

    # Make the original registration token older than the cooldown.
    original_token = create_verification_token(
        test_db,
        user.id,
    )
    test_db.commit()

    original_record = test_db.query(
        EmailVerificationToken
    ).filter_by(
        token_hash=hash_verification_token(original_token)
    ).first()

    original_record.created_at = (
        datetime.now(timezone.utc) - timedelta(minutes=2)
    )
    test_db.commit()

    new_token = resend_verification_token(
        test_db,
        user.email,
    )

    assert new_token is not None
    assert new_token != original_token

    new_record = test_db.query(
        EmailVerificationToken
    ).filter_by(
        token_hash=hash_verification_token(new_token)
    ).first()

    assert new_record is not None
    assert new_record.user_id == user.id
    assert new_record.used_at is None


def test_resend_verification_token_invalidates_previous_token(test_db):
    user = create_test_user(test_db)

    old_token = create_verification_token(test_db, user.id)
    test_db.commit()

    old_record = test_db.query(
        EmailVerificationToken
    ).filter_by(
        token_hash=hash_verification_token(old_token)
    ).first()

    old_record.created_at = (
        datetime.now(timezone.utc) - timedelta(minutes=2)
    )
    test_db.commit()

    new_token = resend_verification_token(
        test_db,
        user.email,
    )

    assert new_token is not None

    test_db.refresh(old_record)

    assert old_record.used_at is not None

    with pytest.raises(InvalidVerificationTokenError):
        verify_email(test_db, old_token)


def test_resend_verification_token_enforces_cooldown(test_db):
    user = create_test_user(test_db)

    create_verification_token(test_db, user.id)
    test_db.commit()

    with pytest.raises(VerificationResendCooldownError):
        resend_verification_token(
            test_db,
            user.email,
        )

    token_count = test_db.query(
        EmailVerificationToken
    ).filter_by(
        user_id=user.id
    ).count()

    assert token_count == 1


def test_resend_verification_token_returns_none_for_unknown_email(test_db):
    result = resend_verification_token(
        test_db,
        "unknown@example.com",
    )

    assert result is None

    token_count = test_db.query(
        EmailVerificationToken
    ).count()

    assert token_count == 0

def test_resend_verification_token_returns_none_for_verified_user(test_db):
    user = create_test_user(test_db)

    user.is_verified = True
    test_db.commit()

    result = resend_verification_token(
        test_db,
        user.email,
    )

    assert result is None

    token_count = test_db.query(
        EmailVerificationToken
    ).filter_by(
        user_id=user.id
    ).count()

    assert token_count == 0
    
def test_resend_verification_token_returns_none_for_inactive_user(test_db):
    user = create_test_user(test_db)

    user.is_active = False
    test_db.commit()

    result = resend_verification_token(
        test_db,
        user.email,
    )

    assert result is None

    token_count = test_db.query(
        EmailVerificationToken
    ).filter_by(
        user_id=user.id
    ).count()

    assert token_count == 0