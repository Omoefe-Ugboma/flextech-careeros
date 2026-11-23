from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app
from app.models.email_verification_token import EmailVerificationToken
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.auth.email_verification import (
    create_verification_token,
    hash_verification_token,
)
from app.services.auth.password import verify_password
from app.services.auth.password_reset import (
    create_password_reset_token,
    hash_password_reset_token,
)
from app.services.auth.refresh import hash_refresh_token
from app.services.email import EmailDeliveryError

def create_client(test_db):
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    return TestClient(app)


def verify_test_user(test_db, email):
    user = test_db.query(User).filter_by(email=email).first()
    assert user is not None

    user.is_verified = True
    test_db.commit()

    return user


def test_forgot_password_returns_generic_response_for_unknown_email(client):
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={
            "email": "unknown@example.com",
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        "message": (
            "If an account exists with that email, "
            "password reset instructions will be sent."
        )
    }



def test_forgot_password_returns_generic_response_for_inactive_user(
    client,
    test_db,
):
    email = "inactive-reset@example.com"

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )

    user = test_db.query(User).filter_by(email=email).first()
    assert user is not None

    user.is_active = False
    test_db.commit()

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": (
            "If an account exists with that email, "
            "password reset instructions will be sent."
        )
    }

    token_count = test_db.query(PasswordResetToken).filter_by(
        user_id=user.id
    ).count()

    assert token_count == 0



def test_register_endpoint(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "apiuser@example.com",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "apiuser@example.com"
    assert "hashed_password" not in data
    assert "password" not in data


def test_duplicate_registration_is_rejected(client):
    payload = {
        "email": "duplicateapi@example.com",
        "password": "StrongPassword123",
    }

    first_response = client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    second_response = client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_login_endpoint(client, test_db):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "loginapi@example.com",
            "password": "StrongPassword123",
        },
    )
    verify_test_user(test_db, "loginapi@example.com")

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "loginapi@example.com",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_rejects_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpassword@example.com",
            "password": "StrongPassword123",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrongpassword@example.com",
            "password": "IncorrectPassword123",
        },
    )

    assert response.status_code == 401


def test_me_endpoint_requires_authentication(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_endpoint_returns_authenticated_user(client, test_db):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "profileapi@example.com",
            "password": "StrongPassword123",
        },
    )

    verify_test_user(test_db, "profileapi@example.com")

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "profileapi@example.com",
            "password": "StrongPassword123",
        },
    )

    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == "profileapi@example.com"
    assert "hashed_password" not in response.json()



def test_login_sets_httponly_refresh_cookie(client, test_db):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "cookieuser@example.com",
            "password": "StrongPassword123",
        },
    )
    verify_test_user(test_db, "cookieuser@example.com")
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "cookieuser@example.com",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 200
    assert "refresh_token" in response.cookies

    set_cookie = response.headers.get("set-cookie", "").lower()
    assert "httponly" in set_cookie


def test_refresh_endpoint_returns_new_access_token(client, test_db):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "refreshapi@example.com",
            "password": "StrongPassword123",
        },
    )

    verify_test_user(test_db, "refreshapi@example.com")

    client.post(
        "/api/v1/auth/login",
        json={
            "email": "refreshapi@example.com",
            "password": "StrongPassword123",
        },
    )

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_forgot_password_creates_reset_token(client, test_db):
    email = "resetuser@example.com"

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )

    user = test_db.query(User).filter_by(email=email).first()
    assert user is not None

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": email},
    )

    assert response.status_code == 200

    token_record = test_db.query(
        PasswordResetToken
    ).filter_by(user_id=user.id).first()

    assert token_record is not None
    assert token_record.used_at is None

def test_forgot_password_sends_reset_email(
    client,
    test_db,
    monkeypatch,
):
    email = "emaildelivery@example.com"
    captured = {}

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )

    def mock_send_password_reset_email(
        recipient,
        recipient_name,
        reset_token,
    ):
        captured["recipient"] = recipient
        captured["recipient_name"] = recipient_name
        captured["reset_token"] = reset_token

    monkeypatch.setattr(
        "app.api.auth.send_password_reset_email",
        mock_send_password_reset_email,
    )

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": email},
    )

    user = test_db.query(User).filter_by(email=email).first()

    token_record = test_db.query(
        PasswordResetToken
    ).filter_by(user_id=user.id).first()

    assert response.status_code == 200
    assert captured["recipient"] == email
    assert captured["recipient_name"] == "emaildelivery"
    assert captured["reset_token"]
    assert token_record.token_hash == hash_password_reset_token(
        captured["reset_token"]
    )

def test_reset_password_rejects_invalid_token(client):
    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": "invalid-reset-token",
            "new_password": "NewStrongPassword456",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Password reset link is invalid or expired."
    )


def test_reset_password_rejects_expired_token(client, test_db):
    email = "expiredreset@example.com"

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )

    user = test_db.query(User).filter_by(email=email).first()
    assert user is not None

    reset_token = create_password_reset_token(
        test_db,
        user.id,
    )

    token_record = test_db.query(PasswordResetToken).filter_by(
        user_id=user.id,
    ).first()

    assert token_record is not None

    token_record.expires_at = (
        datetime.now(timezone.utc) - timedelta(minutes=5)
    )
    test_db.commit()

    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": "NewStrongPassword456",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Password reset link is invalid or expired."
    )



def test_reset_password_successfully_updates_user_password(
    client,
    test_db,
):
    email = "successfulreset@example.com"
    old_password = "StrongPassword123"
    new_password = "NewStrongPassword456"

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": old_password,
        },
    )

    user = test_db.query(User).filter_by(email=email).first()
    assert user is not None

    reset_token = create_password_reset_token(
        test_db,
        user.id,
    )

    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": new_password,
        },
    )

    assert response.status_code == 200

    test_db.refresh(user)

    assert verify_password(
        new_password,
        user.hashed_password,
    )

    assert not verify_password(
        old_password,
        user.hashed_password,
    )


def test_reset_password_revokes_refresh_tokens_through_api(client, test_db):
    email = "resetrevokesessions@example.com"

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )

    user = test_db.query(User).filter_by(email=email).first()
    assert user is not None

    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash="test-reset-api-refresh-token-hash",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_revoked=False,
    )
    test_db.add(refresh_token)

    reset_token = create_password_reset_token(test_db, user.id)
    test_db.commit()

    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": "NewStrongPassword456",
        },
    )

    assert response.status_code == 200

    test_db.refresh(refresh_token)
    assert refresh_token.is_revoked is True

def test_refresh_endpoint_replaces_old_cookie(client, test_db):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "rotationapi@example.com",
            "password": "StrongPassword123",
        },
    )

    verify_test_user(test_db, "rotationapi@example.com")

    client.post(
        "/api/v1/auth/login",
        json={
            "email": "rotationapi@example.com",
            "password": "StrongPassword123",
        },
    )

    old_token = client.cookies.get("refresh_token")

    response = client.post("/api/v1/auth/refresh")

    new_token = client.cookies.get("refresh_token")

    assert response.status_code == 200
    assert old_token is not None
    assert new_token is not None
    assert new_token != old_token


def test_refresh_endpoint_revokes_old_token(client, test_db):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "revocationapi@example.com",
            "password": "StrongPassword123",
        },
    )

    verify_test_user(test_db, "revocationapi@example.com")

    client.post(
        "/api/v1/auth/login",
        json={
            "email": "revocationapi@example.com",
            "password": "StrongPassword123",
        },
    )

    old_token = client.cookies.get("refresh_token")

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 200

    old_record = test_db.query(RefreshToken).filter_by(
        token_hash=hash_refresh_token(old_token)
    ).first()

    assert old_record is not None
    assert old_record.is_revoked is True


def test_refresh_endpoint_rejects_missing_cookie(client):
    client.cookies.clear()

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401


def test_refresh_endpoint_rejects_invalid_cookie(client):
    client.cookies.set(
        "refresh_token",
        "invalid-refresh-token",
        path="/api/v1/auth",
    )

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401

def test_logout_revokes_refresh_token(client, test_db):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "logoutapi@example.com",
            "password": "StrongPassword123",
        },
    )

    verify_test_user(test_db, "logoutapi@example.com")

    client.post(
        "/api/v1/auth/login",
        json={
            "email": "logoutapi@example.com",
            "password": "StrongPassword123",
        },
    )

    old_token = client.cookies.get("refresh_token")

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204

    token_record = test_db.query(RefreshToken).filter_by(
        token_hash=hash_refresh_token(old_token)
    ).first()

    assert token_record is not None
    assert token_record.is_revoked is True


def test_logout_clears_refresh_cookie(client, test_db):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "logoutcookie@example.com",
            "password": "StrongPassword123",
        },
    )

    verify_test_user(test_db, "logoutcookie@example.com")

    client.post(
        "/api/v1/auth/login",
        json={
            "email": "logoutcookie@example.com",
            "password": "StrongPassword123",
        },
    )

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204

    set_cookie = response.headers.get("set-cookie", "").lower()

    assert "refresh_token=" in set_cookie
    assert "max-age=0" in set_cookie


def test_logout_without_cookie_succeeds(client):
    client.cookies.clear()

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204


def test_logout_prevents_refresh_token_reuse(client, test_db):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "logoutreuse@example.com",
            "password": "StrongPassword123",
        },
    )

    verify_test_user(test_db, "logoutreuse@example.com")

    client.post(
        "/api/v1/auth/login",
        json={
            "email": "logoutreuse@example.com",
            "password": "StrongPassword123",
        },
    )

    old_token = client.cookies.get("refresh_token")

    logout_response = client.post("/api/v1/auth/logout")

    assert logout_response.status_code == 204

    client.cookies.set(
        "refresh_token",
        old_token,
        path="/api/v1/auth",
    )

    refresh_response = client.post("/api/v1/auth/refresh")

    assert refresh_response.status_code == 401

def test_login_rejects_unverified_email(client, test_db):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "unverifiedapi@example.com",
            "password": "StrongPassword123",
        },
    )

    user = test_db.query(User).filter_by(
        email="unverifiedapi@example.com"
    ).first()

    assert user is not None
    assert user.is_verified is False

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "unverifiedapi@example.com",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 403
    assert "access_token" not in response.json()
    assert "refresh_token" not in response.cookies

def test_verify_email_endpoint(client, test_db):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "verifyapi@example.com",
            "password": "StrongPassword123",
        },
    )

    user = test_db.query(User).filter_by(
        email="verifyapi@example.com"
    ).first()

    assert user is not None
    assert user.is_verified is False

    verification_token = create_verification_token(
        test_db,
        user.id,
    )
    test_db.commit()

    response = client.post(
        "/api/v1/auth/verify-email",
        json={
            "token": verification_token,
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == "verifyapi@example.com"
    assert response.json()["is_verified"] is True

    test_db.refresh(user)
    assert user.is_verified is True

def test_verify_email_rejects_invalid_token(client):
    response = client.post(
        "/api/v1/auth/verify-email",
        json={
            "token": "this-is-an-invalid-token",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Verification link is invalid or expired."
    )

def test_verify_email_rejects_expired_token(client, test_db):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "expiredverify@example.com",
            "password": "StrongPassword123",
        },
    )

    user = test_db.query(User).filter_by(
        email="expiredverify@example.com"
    ).first()

    assert user is not None

    verification_token = create_verification_token(
        test_db,
        user.id,
    )
    test_db.commit()

    token_record = test_db.query(
        EmailVerificationToken
    ).filter_by(
        token_hash=hash_verification_token(verification_token)
    ).first()

    assert token_record is not None

    token_record.expires_at = (
        datetime.now(timezone.utc) - timedelta(hours=1)
    )
    test_db.commit()

    response = client.post(
        "/api/v1/auth/verify-email",
        json={
            "token": verification_token,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Verification link is invalid or expired."
    )

    test_db.refresh(user)
    assert user.is_verified is False

def test_verify_email_rejects_reused_token(client, test_db):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "reusedverify@example.com",
            "password": "StrongPassword123",
        },
    )

    user = test_db.query(User).filter_by(
        email="reusedverify@example.com"
    ).first()

    assert user is not None

    verification_token = create_verification_token(
        test_db,
        user.id,
    )
    test_db.commit()

    first_response = client.post(
        "/api/v1/auth/verify-email",
        json={
            "token": verification_token,
        },
    )

    assert first_response.status_code == 200
    assert first_response.json()["is_verified"] is True

    second_response = client.post(
        "/api/v1/auth/verify-email",
        json={
            "token": verification_token,
        },
    )

    assert second_response.status_code == 400
    assert second_response.json()["detail"] == (
        "Verification link is invalid or expired."
    )

def test_resend_verification_endpoint_returns_generic_response(
    client,
    test_db,
):
    response = client.post(
        "/api/v1/auth/resend-verification",
        json={
            "email": "resenduser@example.com",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": (
            "If an eligible account exists, "
            "verification instructions will be sent."
        )
    }


def test_resend_verification_endpoint_for_unverified_user(
    client,
    test_db,
):
    email = "unverifiedresend@example.com"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )

    assert register_response.status_code == 201

    user = test_db.query(User).filter_by(email=email).first()
    assert user is not None
    assert user.is_verified is False

    original_token = test_db.query(
        EmailVerificationToken
    ).filter_by(
        user_id=user.id
    ).first()

    assert original_token is not None

    original_token.created_at = (
        datetime.now(timezone.utc) - timedelta(minutes=2)
    )

    test_db.commit()


    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": (
            "If an eligible account exists, "
            "verification instructions will be sent."
        )
    }

    tokens = test_db.query(EmailVerificationToken).filter_by(
        user_id=user.id
    ).all()

    assert len(tokens) == 2


def test_reset_password_rejects_reused_token(client, test_db):
    email = "reusedtoken@example.com"

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )

    user = test_db.query(User).filter_by(email=email).first()
    assert user is not None

    reset_token = create_password_reset_token(
        test_db,
        user.id,
    )

    first_response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": "FirstNewPassword456",
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": "SecondNewPassword789",
        },
    )

    assert second_response.status_code == 400
    assert second_response.json()["detail"] == (
        "Password reset link is invalid or expired."
    )


def test_resend_verification_invalidates_previous_token(
    client,
    test_db,
):
    email = "invalidateprevious@example.com"

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )

    user = test_db.query(User).filter_by(email=email).first()
    assert user is not None

    previous_token = test_db.query(
        EmailVerificationToken
    ).filter_by(
        user_id=user.id
    ).first()

    assert previous_token is not None

    previous_token.created_at = (
        datetime.now(timezone.utc) - timedelta(minutes=2)
    )
    test_db.commit()

    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": email},
    )

    assert response.status_code == 200

    test_db.refresh(previous_token)
    assert previous_token.used_at is not None

def test_resend_verification_cooldown_returns_generic_response(
    client,
    test_db,
):
    email = "cooldownresend@example.com"

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )

    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": (
            "If an eligible account exists, "
            "verification instructions will be sent."
        )
    }

    user = test_db.query(User).filter_by(email=email).first()
    assert user is not None

    tokens = test_db.query(EmailVerificationToken).filter_by(
        user_id=user.id
    ).all()

    assert len(tokens) == 1

def test_resend_verification_for_verified_user_returns_generic_response(
    client,
    test_db,
):
    email = "verifiedresend@example.com"

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )

    user = verify_test_user(test_db, email)

    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": (
            "If an eligible account exists, "
            "verification instructions will be sent."
        )
    }

    tokens = test_db.query(EmailVerificationToken).filter_by(
        user_id=user.id
    ).all()

    assert len(tokens) == 1

def test_resend_verification_for_inactive_user_returns_generic_response(
    client,
    test_db,
):
    email = "inactiveresend@example.com"

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )

    user = test_db.query(User).filter_by(email=email).first()
    assert user is not None

    user.is_active = False
    test_db.commit()

    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": (
            "If an eligible account exists, "
            "verification instructions will be sent."
        )
    }

    tokens = test_db.query(EmailVerificationToken).filter_by(
        user_id=user.id
    ).all()

    assert len(tokens) == 1

def test_forgot_password_handles_email_delivery_failure(
    client,
    test_db,
    monkeypatch,
):
    email = "deliveryfailure@example.com"

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )

    def mock_failed_email_delivery(**kwargs):
        raise EmailDeliveryError("Simulated provider failure")

    monkeypatch.setattr(
        "app.api.auth.send_password_reset_email",
        mock_failed_email_delivery,
    )

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": email},
    )

    user = test_db.query(User).filter_by(email=email).first()

    token_record = test_db.query(
        PasswordResetToken
    ).filter_by(user_id=user.id).first()

    assert response.status_code == 200
    assert "message" in response.json()
    assert token_record is not None
    assert token_record.used_at is None

def test_resend_verification_sends_email(
    client,
    test_db,
    monkeypatch,
):
    email = "resenddelivery@example.com"
    captured_email = {}

    def mock_send_verification_email(**kwargs):
        captured_email.update(kwargs)

    monkeypatch.setattr(
        "app.api.auth.send_verification_email",
        mock_send_verification_email,
    )

    # Register an unverified user.
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )

    user = test_db.query(User).filter_by(
        email=email
    ).first()

    assert user is not None

    # Move the original token outside the resend cooldown.
    original_token = test_db.query(
        EmailVerificationToken
    ).filter_by(
        user_id=user.id
    ).first()

    assert original_token is not None

    original_token.created_at = (
        datetime.now(timezone.utc) - timedelta(minutes=2)
    )
    test_db.commit()

    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": email},
    )

    assert response.status_code == 200

    # Confirm the email service was called correctly.
    assert captured_email["recipient"] == email
    assert captured_email["recipient_name"] == "resenddelivery"
    assert captured_email["verification_token"]

    # Confirm the raw token matches the hashed database token.
    stored_token = test_db.query(
        EmailVerificationToken
    ).filter_by(
        user_id=user.id,
        token_hash=hash_verification_token(
            captured_email["verification_token"]
        ),
    ).first()

    assert stored_token is not None

    # The API must never expose the raw verification token.
    assert captured_email["verification_token"] not in response.text

def test_resend_verification_handles_email_delivery_failure(
    client,
    test_db,
    monkeypatch,
):
    email = "resendfailure@example.com"

    def mock_send_verification_email(**kwargs):
        raise EmailDeliveryError("Simulated email failure")

    monkeypatch.setattr(
        "app.api.auth.send_verification_email",
        mock_send_verification_email,
    )

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )

    user = test_db.query(User).filter_by(
        email=email
    ).first()

    assert user is not None

    original_token = test_db.query(
        EmailVerificationToken
    ).filter_by(
        user_id=user.id
    ).first()

    assert original_token is not None

    original_token.created_at = (
        datetime.now(timezone.utc) - timedelta(minutes=2)
    )
    test_db.commit()

    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": email},
    )

    assert response.status_code == 200

    assert response.json() == {
        "message": (
            "If an eligible account exists, "
            "verification instructions will be sent."
        )
    }

    tokens = test_db.query(
        EmailVerificationToken
    ).filter_by(
        user_id=user.id
    ).all()

    assert len(tokens) == 2

    test_db.refresh(user)
    assert user.is_verified is False

    assert "Simulated email failure" not in response.text
