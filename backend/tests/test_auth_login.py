
import pytest

from app.models.user import User
from app.schemas.auth import UserLogin
from app.services.auth.login import (
    authenticate_user,
    InvalidCredentialsError,
    InactiveAccountError,
    EmailNotVerifiedError,
)
from app.services.auth.token import decode_access_token


def create_user(
    test_db,
    email="login@example.com",
    active=True,
    verified=True,
):
    user = User(
        email=email,
        hashed_password="$argon2id$invalid-test-hash",
        is_active=active,
        is_verified=verified,
    )

    from app.services.auth.password import hash_password

    user.hashed_password = hash_password("StrongPassword123")

    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    return user


def test_successful_login_returns_user_and_access_token(test_db):
    user = create_user(test_db)

    login_data = UserLogin(
        email="login@example.com",
        password="StrongPassword123",
    )

    authenticated_user, token = authenticate_user(
        test_db,
        login_data,
    )

    assert authenticated_user.id == user.id
    assert authenticated_user.email == user.email

    payload = decode_access_token(token)

    assert payload["sub"] == str(user.id)


def test_login_rejects_incorrect_password(test_db):
    create_user(test_db)

    login_data = UserLogin(
        email="login@example.com",
        password="WrongPassword123",
    )

    with pytest.raises(InvalidCredentialsError):
        authenticate_user(test_db, login_data)


def test_login_rejects_unknown_email(test_db):
    login_data = UserLogin(
        email="unknown@example.com",
        password="StrongPassword123",
    )

    with pytest.raises(InvalidCredentialsError):
        authenticate_user(test_db, login_data)


def test_login_rejects_inactive_account(test_db):
    create_user(test_db, active=False)

    login_data = UserLogin(
        email="login@example.com",
        password="StrongPassword123",
    )

    with pytest.raises(InactiveAccountError):
        authenticate_user(test_db, login_data)

def test_login_rejects_unverified_email(test_db):
    create_user(
        test_db,
        verified=False,
    )

    login_data = UserLogin(
        email="login@example.com",
        password="StrongPassword123",
    )

    with pytest.raises(EmailNotVerifiedError):
        authenticate_user(test_db, login_data)