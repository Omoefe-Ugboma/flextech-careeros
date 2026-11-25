
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.authorization import (
    require_verified_organization_role,
)
from app.core.database import get_db
from app.models import JobDescription
from app.models.organization import Organization
from app.models.user import User
from app.schemas.job_description import (
    JobDescriptionCreate,
    JobDescriptionRead,
)
from app.services.job_description.ai_extractor import (
    extract_job_requirements,
)

router = APIRouter(
    prefix="/api/v1/job-descriptions",
    tags=["Job Descriptions"],
)

require_company_access = require_verified_organization_role(
    ["company_admin", "recruiter"]
)


@router.post(
    "",
    response_model=JobDescriptionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_job_description(
    job_data: JobDescriptionCreate,
    organization_id: int,
    current_user: User = Depends(require_company_access),
    db: Session = Depends(get_db),
):
    # The authorization dependency has already verified
    # the user's membership and organization status.
    organization = db.get(Organization, organization_id)

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    # Always use the verified organization's name.
    # Do not trust a company name supplied by the client.
    job_description = JobDescription(
        organization_id=organization.id,
        job_title=job_data.job_title,
        company_name=organization.name,
        location=job_data.location,
        original_description=job_data.original_description,
        processing_status="pending",
    )

    try:
        db.add(job_description)
        db.commit()
        db.refresh(job_description)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save job description.",
        )

    # Extract structured requirements using OpenAI.
    try:
        extracted_information = extract_job_requirements(
            job_description.original_description
        )

        job_description.extracted_data = (
            extracted_information.model_dump(mode="json")
        )

        job_description.processing_status = "processed"

    except Exception:
        job_description.processing_status = "extraction_failed"

    # Save extraction result or failure status.
    try:
        db.commit()
        db.refresh(job_description)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save job extraction results.",
        )

    return job_description


@router.get(
    "",
    response_model=list[JobDescriptionRead],
)
def list_job_descriptions(
    organization_id: int,
    current_user: User = Depends(require_company_access),
    db: Session = Depends(get_db),
):
    statement = (
        select(JobDescription)
        .where(
            JobDescription.organization_id == organization_id
        )
        .order_by(JobDescription.created_at.desc())
    )

    return db.scalars(statement).all()


@router.get(
    "/{job_description_id}",
    response_model=JobDescriptionRead,
)
def get_job_description(
    job_description_id: int,
    organization_id: int,
    current_user: User = Depends(require_company_access),
    db: Session = Depends(get_db),
):
    statement = select(JobDescription).where(
        JobDescription.id == job_description_id,
        JobDescription.organization_id == organization_id,
    )

    job_description = db.scalar(statement)

    if job_description is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job description not found.",
        )

    return job_description
