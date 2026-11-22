import hashlib
import secrets

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.email_verification_token import EmailVerificationToken


VERIFICATION_TOKEN_EXPIRE_HOURS = 24

VERIFICATION_RESEND_COOLDOWN_SECONDS = 60

class InvalidVerificationTokenError(Exception):
    """Raised when an email verification token is invalid."""

class VerificationResendCooldownError(Exception):
    """Raised when a verification resend is requested too soon."""

def hash_verification_token(token: str) -> str:
    """Return the SHA-256 hash of a verification token."""
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()



def create_verification_token(
    db: Session,
    user_id: int,
) -> str:
    """
    Generate a secure verification token and add its hash
    to the current database transaction.
    """

    raw_token = secrets.token_urlsafe(48)

    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=VERIFICATION_TOKEN_EXPIRE_HOURS
    )

    token_record = EmailVerificationToken(
        user_id=user_id,
        token_hash=hash_verification_token(raw_token),
        expires_at=expires_at,
    )

    db.add(token_record)

    return raw_token



def verify_email(
    db: Session,
    raw_token: str,
) -> User:
    """
    Validate an email verification token and verify the user.
    Consume the token within a database transaction.
    """

    try:
        token_hash = hash_verification_token(raw_token)

        token_record = db.scalar(
            select(EmailVerificationToken)
            .where(
                EmailVerificationToken.token_hash == token_hash
            )
            .with_for_update()
        )

        if token_record is None:
            raise InvalidVerificationTokenError(
                "Verification link is invalid or expired."
            )

        now = datetime.now(timezone.utc)
        expires_at = token_record.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if token_record.used_at is not None or expires_at <= now:
            raise InvalidVerificationTokenError(
                "Verification link is invalid or expired."
            )

        user = db.get(User, token_record.user_id)

        if user is None:
            raise InvalidVerificationTokenError(
                "Verification link is invalid or expired."
            )

        user.is_verified = True
        token_record.used_at = now

        db.commit()
        db.refresh(user)

        return user

    except Exception:
        db.rollback()
        raise
    

def resend_verification_token(
    db: Session,
    email: str,
) -> str | None:
    """
    Generate a new verification token for an unverified user.

    Invalidates previous unused tokens and enforces a
    cooldown between resend requests.
    """

    try:
        normalized_email = email.strip().lower()

        user = db.scalar(
            select(User)
            .where(User.email == normalized_email)
            .with_for_update()
        )

        # Return None for unknown or already verified accounts.
        if user is None or user.is_verified or not user.is_active:
            return None

        now = datetime.now(timezone.utc)

        latest_token = db.scalar(
            select(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == user.id
            )
            .order_by(EmailVerificationToken.created_at.desc())
            .limit(1)
        )

        if latest_token is not None:
            created_at = latest_token.created_at

            if created_at.tzinfo is None:
                created_at = created_at.replace(
                    tzinfo=timezone.utc
                )

            elapsed_seconds = (
                now - created_at
            ).total_seconds()

            if elapsed_seconds < VERIFICATION_RESEND_COOLDOWN_SECONDS:
                raise VerificationResendCooldownError(
                    "Please wait before requesting another verification email."
                )

        db.execute(
            update(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == user.id,
                EmailVerificationToken.used_at.is_(None),
            )
            .values(used_at=now)
        )

        raw_token = create_verification_token(
            db,
            user.id,
        )

        db.commit()

        return raw_token

    except Exception:
        db.rollback()
        raise