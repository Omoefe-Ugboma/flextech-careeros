
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import JobDescription
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


@router.post(
    "",
    response_model=JobDescriptionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_job_description(
    job_data: JobDescriptionCreate,
    db: Session = Depends(get_db),
):
    # 1. Save the original job description first.
    job_description = JobDescription(
        job_title=job_data.job_title,
        company_name=job_data.company_name,
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

    # 2. Extract structured requirements using OpenAI.
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

    # 3. Save the extraction result or failure status.
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
    db: Session = Depends(get_db),
):
    statement = select(JobDescription).order_by(
        JobDescription.created_at.desc()
    )

    return db.scalars(statement).all()


@router.get(
    "/{job_description_id}",
    response_model=JobDescriptionRead,
)
def get_job_description(
    job_description_id: int,
    db: Session = Depends(get_db),
):
    job_description = db.get(
        JobDescription,
        job_description_id,
    )

    if job_description is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job description not found.",
        )

    return job_description
