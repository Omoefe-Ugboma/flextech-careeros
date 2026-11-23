import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.auth.password import hash_password

PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30


class InvalidPasswordResetTokenError(Exception):
    """Raised when a password reset token is invalid or expired."""


def hash_password_reset_token(token: str) -> str:
    """Return the SHA-256 hash of a password reset token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token(
    db: Session,
    user_id: int,
) -> str:
    """
    Generate a secure password reset token.

    Store only its SHA-256 hash.
    The caller controls the database transaction.
    """
    raw_token = secrets.token_urlsafe(48)

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )

    token_record = PasswordResetToken(
        user_id=user_id,
        token_hash=hash_password_reset_token(raw_token),
        expires_at=expires_at,
    )

    db.add(token_record)
    db.flush()

    return raw_token

def validate_password_reset_token(
    db: Session,
    raw_token: str,
) -> PasswordResetToken:
    """
    Validate a password reset token.

    Reject missing, expired, or previously used tokens.
    The caller controls the database transaction.
    """

    token_hash = hash_password_reset_token(raw_token)

    token_record = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash)
        .with_for_update()
    )

    if token_record is None:
        raise InvalidPasswordResetTokenError(
            "Invalid password reset token."
        )

    now = datetime.now(timezone.utc)
    expires_at = token_record.expires_at

    # SQLite may return a naive datetime.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    if token_record.used_at is not None or expires_at <= now:
        raise InvalidPasswordResetTokenError(
            "Invalid password reset token."
        )

    return token_record


def reset_user_password(
    db: Session,
    raw_token: str,
    new_password: str,
) -> None:
    """
    Reset a user's password and revoke all active refresh tokens.

    All database changes are committed atomically.
    """

    try:
        # Read the token first without acquiring a row lock.
        # We only need its user_id to determine which user to lock.
        token_hash = hash_password_reset_token(raw_token)

        token_record = db.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash
            )
        )

        if token_record is None:
            raise InvalidPasswordResetTokenError(
                "Invalid password reset token."
            )

        # Lock the user row first.
        user = db.scalar(
            select(User)
            .where(User.id == token_record.user_id)
            .with_for_update()
        )

        if user is None or not user.is_active:
            raise InvalidPasswordResetTokenError(
                "Invalid password reset token."
            )

        # Now lock and validate the reset token.
        # This checks whether it has expired or already been used.
        token_record = validate_password_reset_token(
            db,
            raw_token,
        )
        
        if token_record.user_id != user.id:
            raise InvalidPasswordResetTokenError(
                "Invalid password reset token."
            )
        
        # Update the password using the existing Argon2 service.
        user.hashed_password = hash_password(new_password)

        # Mark the reset token as used.
        now = datetime.now(timezone.utc)
        token_record.used_at = now

        # Invalidate every other outstanding reset token.
        db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.id != token_record.id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=now)
        )

        # Revoke every active refresh token belonging to this user.
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user.id,
            RefreshToken.is_revoked.is_(False),
        ).update(
            {RefreshToken.is_revoked: True},
            synchronize_session=False,
        )

        db.commit()

    except Exception:
        db.rollback()
        raise
