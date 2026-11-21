
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.auth.password import hash_password
from app.services.auth.token import create_access_token


auth_test_app = FastAPI()


@auth_test_app.get("/protected")
def protected_route(
    current_user: User = Depends(get_current_user),
):
    return {
        "user_id": current_user.id,
        "email": current_user.email,
    }


def create_test_client(test_db):
    def override_get_db():
        yield test_db

    auth_test_app.dependency_overrides[get_db] = override_get_db

    return TestClient(auth_test_app)


def create_test_user(test_db):
    user = User(
        email="auth-test@example.com",
        hashed_password=hash_password("StrongPassword123"),
        is_active=True,
        is_verified=True,
    )

    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    return user


def test_authenticated_user_can_access_protected_route(test_db):
    user = create_test_user(test_db)
    token = create_access_token(user.id)

    client = create_test_client(test_db)

    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == user.id
    assert response.json()["email"] == user.email

    auth_test_app.dependency_overrides.clear()


def test_request_without_token_is_rejected(test_db):
    client = create_test_client(test_db)

    response = client.get("/protected")

    assert response.status_code == 401

    auth_test_app.dependency_overrides.clear()


def test_inactive_user_is_rejected(test_db):
    user = create_test_user(test_db)
    user.is_active = False
    test_db.commit()

    token = create_access_token(user.id)
    client = create_test_client(test_db)

    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401

    auth_test_app.dependency_overrides.clear()


def test_unknown_user_is_rejected(test_db):
    token = create_access_token(user_id=99999)
    client = create_test_client(test_db)

    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401

    auth_test_app.dependency_overrides.clear()
