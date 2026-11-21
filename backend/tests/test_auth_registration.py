
import pytest

from sqlalchemy import select

from app.models.user import User
from app.models.user_role import UserRole
from app.models.email_verification_token import EmailVerificationToken
from app.schemas.auth import UserRegister
from app.services.auth.registration import (
    EmailAlreadyRegisteredError,
    register_user,
)
from app.services.auth.email_verification import hash_verification_token
from app.services.auth.password import verify_password


def test_register_user_successfully(test_db):
    user_data = UserRegister(
        email="newuser@example.com",
        password="StrongPassword123",
    )

    user, verification_token = register_user(test_db, user_data)

    assert user.id is not None
    assert user.email == "newuser@example.com"
    assert user.is_active is True
    assert user.is_verified is False
    assert user.hashed_password != "StrongPassword123"
    assert isinstance(verification_token, str)


def test_register_user_assigns_job_seeker_role(test_db):
    user_data = UserRegister(
        email="jobseeker@example.com",
        password="StrongPassword123",
    )

    user, _ = register_user(test_db, user_data)

    role = test_db.scalar(
        select(UserRole).where(UserRole.user_id == user.id)
    )

    assert role is not None
    assert role.role == "job_seeker"


def test_register_user_creates_verification_token(test_db):
    user_data = UserRegister(
        email="verification@example.com",
        password="StrongPassword123",
    )

    user, raw_token = register_user(test_db, user_data)

    stored_token = test_db.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user.id
        )
    )

    assert stored_token is not None
    assert stored_token.token_hash == hash_verification_token(raw_token)
    assert stored_token.token_hash != raw_token
    assert stored_token.used_at is None


def test_register_user_rejects_duplicate_email(test_db):
    user_data = UserRegister(
        email="duplicate@example.com",
        password="StrongPassword123",
    )

    register_user(test_db, user_data)

    with pytest.raises(EmailAlreadyRegisteredError):
        register_user(test_db, user_data)


def test_register_user_normalizes_email(test_db):
    user_data = UserRegister(
        email="NewUser@Example.com",
        password="StrongPassword123",
    )

    user, _ = register_user(test_db, user_data)

    assert user.email == "newuser@example.com"


def test_registered_password_can_be_verified(test_db):
    password = "StrongPassword123"

    user_data = UserRegister(
        email="passwordtest@example.com",
        password=password,
    )

    user, _ = register_user(test_db, user_data)

    assert verify_password(password, user.hashed_password)
