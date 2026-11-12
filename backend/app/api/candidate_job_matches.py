
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

from app.schemas.candidate_job_match import (
    CandidateJobMatchCreate,
    CandidateJobMatchRead,
)

from app.services.matching.match_service import (
    run_candidate_job_match,
)


router = APIRouter(
    prefix="/api/v1/candidate-job-matches",
    tags=["Candidate Job Matches"],
)


@router.post(
    "",
    response_model=CandidateJobMatchRead,
    status_code=201,
)
def create_candidate_job_match(
    match_data: CandidateJobMatchCreate,
    db: Session = Depends(get_db),
):
    return run_candidate_job_match(
        db=db,
        candidate_id=match_data.candidate_id,
        cv_document_id=match_data.cv_document_id,
        job_description_id=match_data.job_description_id,
    )
