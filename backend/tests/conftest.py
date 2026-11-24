
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.api import auth
from app.services.auth.token import create_access_token

@pytest.fixture
def test_db():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()

    yield db

    db.close()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture
def client(test_db):
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()



@pytest.fixture(autouse=True)
def disable_real_email_delivery(monkeypatch):
    def mock_email_delivery(**kwargs):
        return None

    monkeypatch.setattr(
        auth,
        "send_verification_email",
        mock_email_delivery,
    )

    monkeypatch.setattr(
        auth,
        "send_password_reset_email",
        mock_email_delivery,
    )
    
@pytest.fixture
def authenticated_client(client, test_db):
    from app.models.user import User
    from app.models.user_role import UserRole

    def create_authenticated_user(
        email="jobseeker@example.com",
        role="job_seeker",
    ):
        user = User(
            email=email,
            hashed_password="test-password-hash",
            is_active=True,
            is_verified=True,
        )

        test_db.add(user)
        test_db.flush()

        test_db.add(
            UserRole(
                user_id=user.id,
                role=role,
            )
        )

        test_db.commit()

        access_token = create_access_token(user.id)

        return user, {
            "Authorization": f"Bearer {access_token}"
        }

    return create_authenticated_user