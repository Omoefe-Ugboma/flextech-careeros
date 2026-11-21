
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.auth import UserRegister
from app.services.auth.password import hash_password
from app.services.auth.email_verification import (
    create_verification_token,
)


class EmailAlreadyRegisteredError(Exception):
    """Raised when an email address already belongs to an account."""


def register_user(
    db: Session,
    user_data: UserRegister,
) -> tuple[User, str]:
    """
    Register an individual job seeker.

    Creates the user, assigns the default role, and creates
    an email verification token in one database transaction.

    Returns the user and raw verification token internally.
    """

    normalized_email = str(user_data.email).strip().lower()

    try:
        existing_user = db.scalar(
            select(User).where(User.email == normalized_email)
        )

        if existing_user:
            raise EmailAlreadyRegisteredError(
                "An account with this email already exists."
            )

        user = User(
            email=normalized_email,
            hashed_password=hash_password(user_data.password),
            is_active=True,
            is_verified=False,
        )

        db.add(user)
        db.flush()

        role = UserRole(
            user_id=user.id,
            role="job_seeker",
        )

        db.add(role)

        verification_token = create_verification_token(
            db,
            user.id,
        )

        db.commit()
        db.refresh(user)

        return user, verification_token

    except IntegrityError:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise
