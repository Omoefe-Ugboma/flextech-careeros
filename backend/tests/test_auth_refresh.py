
from datetime import datetime, timedelta, timezone

from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.services.auth.refresh import (
    create_refresh_token,
    hash_refresh_token,
    validate_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
    InvalidRefreshTokenError
)
import pytest

def create_test_user(test_db):
    user = User(
        email="refresh@example.com",
        hashed_password="test-password-hash",
        is_active=True,
        is_verified=True,
    )

    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    return user


def test_create_refresh_token(test_db):
    user = create_test_user(test_db)

    raw_token = create_refresh_token(test_db, user.id)

    assert isinstance(raw_token, str)
    assert len(raw_token) > 0

    token_hash = hash_refresh_token(raw_token)

    stored_token = test_db.query(RefreshToken).filter_by(
        token_hash=token_hash
    ).first()

    assert stored_token is not None
    assert stored_token.user_id == user.id
    assert stored_token.is_revoked is False


def test_refresh_token_is_stored_as_hash(test_db):
    user = create_test_user(test_db)

    raw_token = create_refresh_token(test_db, user.id)

    stored_tokens = test_db.query(RefreshToken).all()

    assert raw_token not in [
        token.token_hash for token in stored_tokens
    ]


def test_validate_valid_refresh_token(test_db):
    user = create_test_user(test_db)

    raw_token = create_refresh_token(test_db, user.id)

    token_record = validate_refresh_token(
        test_db,
        raw_token,
    )

    assert token_record is not None
    assert token_record.user_id == user.id


def test_reject_unknown_refresh_token(test_db):
    token_record = validate_refresh_token(
        test_db,
        "unknown-refresh-token",
    )

    assert token_record is None


def test_reject_expired_refresh_token(test_db):
    user = create_test_user(test_db)

    token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token("expired-token"),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        is_revoked=False,
    )

    test_db.add(token_record)
    test_db.commit()

    result = validate_refresh_token(
        test_db,
        "expired-token",
    )

    assert result is None


def test_reject_revoked_refresh_token(test_db):
    user = create_test_user(test_db)

    raw_token = create_refresh_token(test_db, user.id)

    token_record = validate_refresh_token(
        test_db,
        raw_token,
    )

    revoke_refresh_token(test_db, token_record)

    result = validate_refresh_token(
        test_db,
        raw_token,
    )

    assert result is None


def test_rotate_refresh_token_returns_new_tokens(test_db):
    user = create_test_user(test_db)
    old_token = create_refresh_token(test_db, user.id)

    new_access_token, new_refresh_token = rotate_refresh_token(
        test_db,
        old_token,
    )

    assert isinstance(new_access_token, str)
    assert len(new_access_token) > 0

    assert isinstance(new_refresh_token, str)
    assert len(new_refresh_token) > 0

    assert new_refresh_token != old_token


def test_rotation_revokes_old_refresh_token(test_db):
    user = create_test_user(test_db)
    old_token = create_refresh_token(test_db, user.id)

    rotate_refresh_token(test_db, old_token)

    assert validate_refresh_token(test_db, old_token) is None


def test_rotation_creates_valid_replacement_token(test_db):
    user = create_test_user(test_db)
    old_token = create_refresh_token(test_db, user.id)

    _, new_refresh_token = rotate_refresh_token(
        test_db,
        old_token,
    )

    replacement = validate_refresh_token(
        test_db,
        new_refresh_token,
    )

    assert replacement is not None
    assert replacement.user_id == user.id


def test_rotation_rejects_reuse_of_old_token(test_db):
    user = create_test_user(test_db)
    old_token = create_refresh_token(test_db, user.id)

    rotate_refresh_token(test_db, old_token)

    with pytest.raises(InvalidRefreshTokenError):
        rotate_refresh_token(test_db, old_token)


def test_rotation_rejects_unknown_token(test_db):
    with pytest.raises(InvalidRefreshTokenError):
        rotate_refresh_token(
            test_db,
            "unknown-refresh-token",
        )


def test_rotation_rejects_inactive_user(test_db):
    user = create_test_user(test_db)
    old_token = create_refresh_token(test_db, user.id)

    user.is_active = False
    test_db.commit()

    with pytest.raises(InvalidRefreshTokenError):
        rotate_refresh_token(test_db, old_token)

    # The rejected token must remain valid in the database.
    # It must not be revoked by a failed rotation.
    token_record = test_db.query(RefreshToken).filter_by(
        token_hash=hash_refresh_token(old_token)
    ).first()

    assert token_record is not None
    assert token_record.is_revoked is False

