from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db
from app.models.refresh_token import RefreshToken
from app.services.auth.refresh import hash_refresh_token
from app.models.user import User
from datetime import datetime, timedelta, timezone
from app.models.email_verification_token import EmailVerificationToken
from app.services.auth.email_verification import (
    create_verification_token,
    hash_verification_token,
)

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
    
