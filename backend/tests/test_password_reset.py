from datetime import datetime, timedelta, timezone

import pytest

from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.auth.password import hash_password, verify_password
from app.services.auth.password_reset import (
    InvalidPasswordResetTokenError,
    create_password_reset_token,
    hash_password_reset_token,
    reset_user_password,
    validate_password_reset_token,
)

def create_test_user(test_db):
    user = User(
        email="password-reset-test@example.com",
        hashed_password=hash_password("TestPassword123"),
        is_active=True,
        is_verified=True,
    )

    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    return user


def test_password_reset_token_is_generated(test_db):
    user = create_test_user(test_db)

    raw_token = create_password_reset_token(
        test_db,
        user.id,
    )

    assert isinstance(raw_token, str)
    assert len(raw_token) > 40


def test_password_reset_token_is_stored_as_hash(test_db):
    user = create_test_user(test_db)

    raw_token = create_password_reset_token(
        test_db,
        user.id,
    )

    token_record = test_db.query(
        PasswordResetToken
    ).filter_by(user_id=user.id).first()

    assert token_record is not None
    assert token_record.token_hash != raw_token
    assert token_record.token_hash == hash_password_reset_token(
        raw_token
    )


def test_password_reset_token_hash_is_deterministic():
    token = "sample-reset-token"

    first_hash = hash_password_reset_token(token)
    second_hash = hash_password_reset_token(token)

    assert first_hash == second_hash



def test_valid_password_reset_token_is_accepted(test_db):
    user = create_test_user(test_db)

    raw_token = create_password_reset_token(
        test_db,
        user.id,
    )

    token_record = validate_password_reset_token(
        test_db,
        raw_token,
    )

    assert token_record is not None
    assert token_record.user_id == user.id
    assert token_record.used_at is None


def test_unknown_password_reset_token_is_rejected(test_db):

    with pytest.raises(InvalidPasswordResetTokenError):
        validate_password_reset_token(
            test_db,
            "this-token-does-not-exist",
        )


def test_expired_password_reset_token_is_rejected(test_db):
    user = create_test_user(test_db)

    raw_token = create_password_reset_token(
        test_db,
        user.id,
    )

    token_record = test_db.query(
        PasswordResetToken
    ).filter_by(user_id=user.id).first()

    token_record.expires_at = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    )
    test_db.commit()

    with pytest.raises(InvalidPasswordResetTokenError):
        validate_password_reset_token(
            test_db,
            raw_token,
        )


def test_previously_used_password_reset_token_is_rejected(test_db):
    user = create_test_user(test_db)

    raw_token = create_password_reset_token(
        test_db,
        user.id,
    )

    token_record = test_db.query(
        PasswordResetToken
    ).filter_by(user_id=user.id).first()

    token_record.used_at = datetime.now(timezone.utc)
    test_db.commit()

    with pytest.raises(InvalidPasswordResetTokenError):
        validate_password_reset_token(
            test_db,
            raw_token,
        )


def test_password_reset_updates_user_password(test_db):
    user = create_test_user(test_db)
    old_password_hash = user.hashed_password

    raw_token = create_password_reset_token(
        test_db,
        user.id,
    )

    new_password = "NewSecurePassword456"

    reset_user_password(
        test_db,
        raw_token,
        new_password,
    )

    test_db.refresh(user)

    assert user.hashed_password != old_password_hash
    assert verify_password(
        new_password,
        user.hashed_password,
    ) is True
    assert verify_password(
        "TestPassword123",
        user.hashed_password,
    ) is False


def test_password_reset_revokes_all_active_refresh_tokens(test_db):
    user = create_test_user(test_db)

    active_token_one = RefreshToken(
        user_id=user.id,
        token_hash="test-refresh-token-hash-one",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_revoked=False,
    )

    active_token_two = RefreshToken(
        user_id=user.id,
        token_hash="test-refresh-token-hash-two",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_revoked=False,
    )

    test_db.add_all([
        active_token_one,
        active_token_two,
    ])
    test_db.commit()

    raw_token = create_password_reset_token(
        test_db,
        user.id,
    )

    reset_user_password(
        test_db,
        raw_token,
        "NewSecurePassword456",
    )

    test_db.refresh(active_token_one)
    test_db.refresh(active_token_two)

    assert active_token_one.is_revoked is True
    assert active_token_two.is_revoked is True

def test_password_reset_invalidates_other_outstanding_tokens(test_db):
    user = create_test_user(test_db)

    first_token = create_password_reset_token(
        test_db,
        user.id,
    )

    second_token = create_password_reset_token(
        test_db,
        user.id,
    )

    reset_user_password(
        test_db,
        first_token,
        "NewSecurePassword456",
    )

    tokens = test_db.query(
        PasswordResetToken
    ).filter_by(
        user_id=user.id
    ).all()

    assert len(tokens) == 2

    for token_record in tokens:
        assert token_record.used_at is not None

    with pytest.raises(InvalidPasswordResetTokenError):
        validate_password_reset_token(
            test_db,
            second_token,
        )
        

def test_inactive_user_cannot_reset_password(test_db):
    user = create_test_user(test_db)
    user.is_active = False
    test_db.commit()

    original_password = user.hashed_password

    reset_token = create_password_reset_token(
        test_db,
        user.id,
    )
    
    test_db.commit()

    token_hash = hash_password_reset_token(reset_token)

    token_record = test_db.query(
        PasswordResetToken
    ).filter_by(
        token_hash=token_hash,
    ).first()

    assert token_record is not None

    with pytest.raises(InvalidPasswordResetTokenError):
        reset_user_password(
            test_db,
            reset_token,
            "NewSecurePassword456",
        )

    test_db.refresh(user)
    test_db.refresh(token_record)

    assert user.hashed_password == original_password
    assert token_record.used_at is None



