from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Candidate,
    CVDocument,
    JobDescription,
    CandidateJobMatch,
)

from app.services.matching.match_engine import (
    build_complete_match_result,
)

def get_approved_cv(
    db: Session,
    candidate_id: int,
    cv_document_id: int,
) -> CVDocument:

    # 1. Verify that the candidate exists.
    candidate = db.get(Candidate, candidate_id)

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found.",
        )

    # 2. Retrieve a CV belonging to this candidate.
    statement = select(CVDocument).where(
        CVDocument.id == cv_document_id,
        CVDocument.candidate_id == candidate_id,
    )

    cv_document = db.scalar(statement)

    if cv_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV document not found for this candidate.",
        )

    # 3. Verify that CV processing succeeded.
    if cv_document.processing_status != "processed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CV document has not been processed successfully.",
        )

    # 4. Verify human approval.
    if (
        cv_document.review_status != "approved"
        or not cv_document.approved_data
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CV document has not been approved or contains no approved data.",
        )

    return cv_document

def get_processed_job_description(
    db: Session,
    job_description_id: int,
) -> JobDescription:

    # 1. Retrieve the job description.
    job_description = db.get(
        JobDescription,
        job_description_id,
    )

    if job_description is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job description not found.",
        )

    # 2. Verify that AI extraction succeeded.
    if (
        job_description.processing_status != "processed"
        or not job_description.extracted_data
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job description has not been processed successfully.",
        )

    return job_description

def run_candidate_job_match(
    db: Session,
    candidate_id: int,
    cv_document_id: int,
    job_description_id: int,
) -> dict:

    # 1. Retrieve and validate the candidate's approved CV.
    cv_document = get_approved_cv(
        db=db,
        candidate_id=candidate_id,
        cv_document_id=cv_document_id,
    )

    # 2. Retrieve and validate the processed job description.
    job_description = get_processed_job_description(
        db=db,
        job_description_id=job_description_id,
    )

    # 3. Run the matching engine.
    match_results = build_complete_match_result(
        approved_cv=cv_document.approved_data,
        job_data=job_description.extracted_data,
    )

    # 4. Calculate the overall score.
    match_score = match_results["skills"]["required_skills"][
        "required_skill_coverage"
    ]

    # 5. Create a database record.
    match_record = CandidateJobMatch(
        candidate_id=candidate_id,
        cv_document_id=cv_document_id,
        job_description_id=job_description_id,
        match_score=match_score,
        match_results=match_results,
    )

    # 6. Save the assessment.
    try:
        db.add(match_record)
        db.commit()
        db.refresh(match_record)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save candidate-job match.",
        )

    # 7. Return the saved assessment.
    return {
        "id": match_record.id,
        "candidate_id": match_record.candidate_id,
        "cv_document_id": match_record.cv_document_id,
        "job_description_id": match_record.job_description_id,
        "match_score": match_record.match_score,
        "match_results": match_record.match_results,
        "created_at": match_record.created_at,
    }