
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import settings
from app.models.refresh_token import RefreshToken

from app.models.user import User
from app.services.auth.token import create_access_token

class InvalidRefreshTokenError(Exception):
    """Raised when a refresh token cannot be used."""

def hash_refresh_token(token: str) -> str:
    """Return the SHA-256 hash of a refresh token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_refresh_token(
    db: Session,
    user_id: int,
) -> str:
    """
    Generate a random refresh token and store only its hash.
    """

    raw_token = secrets.token_urlsafe(64)

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    token_record = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=expires_at,
        is_revoked=False,
    )

    db.add(token_record)
    db.commit()

    return raw_token


def validate_refresh_token(
    db: Session,
    raw_token: str,
) -> RefreshToken | None:
    """
    Find a valid, unrevoked and unexpired refresh token.
    """

    token_hash = hash_refresh_token(raw_token)

    token_record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash
        )
    )

    if token_record is None:
        return None

    now = datetime.now(timezone.utc)

    expires_at = token_record.expires_at

    # SQLite may return a naive datetime despite timezone=True.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if token_record.is_revoked or expires_at <= now:
        return None

    return token_record


def revoke_refresh_token(
    db: Session,
    token_record: RefreshToken,
) -> None:
    """Revoke a refresh token and persist the change."""

    token_record.is_revoked = True
    db.commit()



def rotate_refresh_token(
    db: Session,
    raw_token: str,
) -> tuple[str, str]:
    """
    Validate and rotate a refresh token atomically.

    Returns:
        A tuple containing the new access token and refresh token.
    """

    try:
        token_hash = hash_refresh_token(raw_token)

        # Lock the existing token row to prevent concurrent reuse.
        token_record = db.scalar(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .with_for_update()
        )

        if token_record is None:
            raise InvalidRefreshTokenError(
                "Invalid refresh token."
            )

        now = datetime.now(timezone.utc)

        expires_at = token_record.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc
            )

        if token_record.is_revoked or expires_at <= now:
            raise InvalidRefreshTokenError(
                "Invalid refresh token."
            )

        user = db.scalar(
            select(User).where(User.id == token_record.user_id)
        )

        if user is None or not user.is_active:
            raise InvalidRefreshTokenError(
                "Invalid refresh token."
            )

        # Revoke the old token.
        token_record.is_revoked = True

        # Generate its replacement.
        new_raw_token = secrets.token_urlsafe(64)

        new_expires_at = now + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        replacement = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(new_raw_token),
            expires_at=new_expires_at,
            is_revoked=False,
        )

        db.add(replacement)

        # Generate a new short-lived access token.
        new_access_token = create_access_token(user.id)

        # Both database changes succeed or fail together.
        db.commit()

        return new_access_token, new_raw_token

    except InvalidRefreshTokenError:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise
