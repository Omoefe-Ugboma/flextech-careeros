
from collections.abc import Callable, Sequence

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization

from app.api.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.organization_membership import OrganizationMembership
from app.models.user import User
from app.models.user_role import UserRole


def require_platform_role(
    allowed_roles: Sequence[str],
) -> Callable:
    """
    Require the authenticated user to have at least one
    of the specified platform roles.
    """

    def role_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:

        statement = select(UserRole).where(
            UserRole.user_id == current_user.id,
            UserRole.role.in_(allowed_roles),
        )

        user_role = db.scalar(statement)

        if user_role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return current_user

    return role_checker


def require_organization_role(
    allowed_roles: Sequence[str],
) -> Callable:
    """
    Require the authenticated user to have an active
    membership with at least one of the specified roles.

    The organization ID must be supplied by the endpoint.
    """

    def role_checker(
        organization_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:

        statement = select(OrganizationMembership).where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.membership_status == "active",
            OrganizationMembership.role.in_(allowed_roles),
        )

        membership = db.scalar(statement)

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this organization.",
            )

        return current_user

    return role_checker


def require_verified_organization_role(
    allowed_roles: Sequence[str],
) -> Callable:
    """
    Require an authenticated user to have an active membership
    in an active and verified organization, with an allowed role.
    """

    def role_checker(
        organization_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:

        organization = db.scalar(
            select(Organization).where(
                Organization.id == organization_id,
                Organization.is_active.is_(True),
                Organization.is_verified.is_(True),
            )
        )

        if organization is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This organization is not authorized to perform this action.",
            )

        membership = db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == current_user.id,
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.membership_status == "active",
                OrganizationMembership.role.in_(allowed_roles),
            )
        )

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this organization.",
            )

        return current_user

    return role_checker
