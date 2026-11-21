
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import UserLogin
from app.services.auth.password import verify_password
from app.services.auth.token import create_access_token


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid."""


class InactiveAccountError(Exception):
    """Raised when an account is inactive."""

class EmailNotVerifiedError(Exception):
    """Raised when a user attempts to log in before verifying their email."""


def authenticate_user(
    db: Session,
    login_data: UserLogin,
) -> tuple[User, str]:
    """
    Authenticate a user and return the user and access token.
    """

    normalized_email = str(login_data.email).strip().lower()

    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if user is None:
        raise InvalidCredentialsError("Invalid email or password.")

    if not verify_password(
        login_data.password,
        user.hashed_password,
    ):
        raise InvalidCredentialsError("Invalid email or password.")

    if not user.is_active:
        raise InactiveAccountError("This account is inactive.")
   
    if not user.is_verified:
        raise EmailNotVerifiedError(
            "Please verify your email address before logging in."
        )
    access_token = create_access_token(user.id)

    return user, access_token
