
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies.authorization import (
    require_platform_role,
    require_organization_role,
)
from app.models.organization_membership import OrganizationMembership
from app.models.user import User
from app.models.user_role import UserRole


def create_test_user(db: Session) -> User:
    user = User(
        email="authorization@example.com",
        hashed_password="test-password-hash",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()
    return user


def test_platform_role_allows_authorized_user(test_db):
    user = create_test_user(test_db)

    test_db.add(
        UserRole(
            user_id=user.id,
            role="platform_admin",
        )
    )
    test_db.commit()

    dependency = require_platform_role(["platform_admin"])

    result = dependency(
        current_user=user,
        db=test_db,
    )

    assert result.id == user.id


def test_platform_role_rejects_unauthorized_user(test_db):
    user = create_test_user(test_db)
    test_db.commit()

    dependency = require_platform_role(["platform_admin"])

    with pytest.raises(HTTPException) as exc_info:
        dependency(
            current_user=user,
            db=test_db,
        )

    assert exc_info.value.status_code == 403


def test_organization_role_allows_active_member(test_db):
    user = create_test_user(test_db)

    membership = OrganizationMembership(
        user_id=user.id,
        organization_id=1,
        role="company_admin",
        membership_status="active",
    )
    test_db.add(membership)
    test_db.commit()

    dependency = require_organization_role(["company_admin"])

    result = dependency(
        organization_id=1,
        current_user=user,
        db=test_db,
    )

    assert result.id == user.id


def test_organization_role_rejects_pending_member(test_db):
    user = create_test_user(test_db)

    membership = OrganizationMembership(
        user_id=user.id,
        organization_id=1,
        role="company_admin",
        membership_status="pending",
    )
    test_db.add(membership)
    test_db.commit()

    dependency = require_organization_role(["company_admin"])

    with pytest.raises(HTTPException) as exc_info:
        dependency(
            organization_id=1,
            current_user=user,
            db=test_db,
        )

    assert exc_info.value.status_code == 403



def test_organization_role_rejects_wrong_role(test_db):
    user = create_test_user(test_db)

    test_db.add(
        OrganizationMembership(
            user_id=user.id,
            organization_id=1,
            role="recruiter",
            membership_status="active",
        )
    )
    test_db.commit()

    dependency = require_organization_role(["company_admin"])

    with pytest.raises(HTTPException) as exc_info:
        dependency(
            organization_id=1,
            current_user=user,
            db=test_db,
        )

    assert exc_info.value.status_code == 403


def test_organization_role_rejects_different_organization(test_db):
    user = create_test_user(test_db)

    test_db.add(
        OrganizationMembership(
            user_id=user.id,
            organization_id=1,
            role="company_admin",
            membership_status="active",
        )
    )
    test_db.commit()

    dependency = require_organization_role(["company_admin"])

    with pytest.raises(HTTPException) as exc_info:
        dependency(
            organization_id=2,
            current_user=user,
            db=test_db,
        )

    assert exc_info.value.status_code == 403


def test_organization_role_rejects_suspended_member(test_db):
    user = create_test_user(test_db)

    test_db.add(
        OrganizationMembership(
            user_id=user.id,
            organization_id=1,
            role="company_admin",
            membership_status="suspended",
        )
    )
    test_db.commit()

    dependency = require_organization_role(["company_admin"])

    with pytest.raises(HTTPException) as exc_info:
        dependency(
            organization_id=1,
            current_user=user,
            db=test_db,
        )

    assert exc_info.value.status_code == 403
