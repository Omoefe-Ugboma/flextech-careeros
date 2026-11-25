
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.user import User

from app.services.auth.registration import (
    hash_password,
    create_verification_token,
    EmailAlreadyRegisteredError,
)


class OrganizationEmailAlreadyRegisteredError(Exception):
    """Raised when a company email is already registered."""


def register_company(
    db: Session,
    company_data,
) -> tuple[User, Organization, str]:
    """
    Register a company and its administrator.

    Creates the user, organization, pending company-admin membership,
    and email verification token in one transaction.

    Returns:
        User, Organization, raw verification token.
    """

    admin_email = str(company_data.admin_email).strip().lower()
    company_email = str(company_data.company_email).strip().lower()

    try:
        # Check whether the administrator's login email already exists.
        existing_user = db.scalar(
            select(User).where(User.email == admin_email)
        )

        if existing_user:
            raise EmailAlreadyRegisteredError(
                "This administrator email is already registered."
            )

        # Check whether the company's official email already exists.
        existing_organization = db.scalar(
            select(Organization).where(
                Organization.company_email == company_email
            )
        )

        if existing_organization:
            raise OrganizationEmailAlreadyRegisteredError(
                "This company email is already registered."
            )

        # 1. Create the administrator's user account.
        user = User(
            email=admin_email,
            hashed_password=hash_password(company_data.password),
            is_active=True,
            is_verified=False,
        )

        db.add(user)
        db.flush()

        # 2. Create the organization.
        organization = Organization(
            name=company_data.company_name.strip(),
            company_email=company_email,
            website=company_data.website,
            description=company_data.description,
            is_active=True,
            is_verified=False,
        )

        db.add(organization)
        db.flush()

        # 3. Create the administrator's pending membership.
        membership = OrganizationMembership(
            user_id=user.id,
            organization_id=organization.id,
            role="company_admin",
            membership_status="pending",
        )

        db.add(membership)

        # 4. Generate the administrator's email verification token.
        verification_token = create_verification_token(db, user.id)

        # 5. Commit all registration records together.
        db.commit()

        db.refresh(user)
        db.refresh(organization)

        return user, organization, verification_token

    except Exception:
        db.rollback()
        raise
