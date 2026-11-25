
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session
from app.schemas.cv_document import CVDocumentRecruiterRead

from app.core.database import get_db
from app.api.dependencies.authorization import (
    require_verified_organization_role,
)
from app.models.user import User
from app.schemas.candidate_access import (
    CandidateAccessRequestCreate,
    CandidateAccessRequestRead,
)
from app.services.candidate_access_service import (
    create_candidate_access_request,
)


from app.api.dependencies.auth import get_current_user

from app.schemas.candidate_access import (
    CandidateAccessDecision,
    CandidateRecruiterRead,
)

from app.services.candidate_access_service import (
    list_candidate_access_requests,
    update_candidate_access_decision,
    get_candidate_for_organization,
    get_approved_cvs_for_organization,
)

router = APIRouter(
    prefix="/api/v1/candidate-access",
    tags=["Candidate Access"],
)


@router.post(
    "/requests",
    response_model=CandidateAccessRequestRead,
    status_code=status.HTTP_201_CREATED,
)
def request_candidate_access(
    request_data: CandidateAccessRequestCreate,
    organization_id: int = Query(gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_verified_organization_role(
            ["company_admin", "recruiter"]
        )
    ),
):
    try:
        access_request = create_candidate_access_request(
            db,
            candidate_id=request_data.candidate_id,
            organization_id=organization_id,
            requested_by_user_id=current_user.id,
        )

        return access_request

    except ValueError as exc:
        message = str(exc)

        if message == "Candidate not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        )

@router.get(
    "/requests/mine",
    response_model=list[CandidateAccessRequestRead],
)
def get_my_candidate_access_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_candidate_access_requests(
        db,
        candidate_owner_user_id=current_user.id,
    )


@router.patch(
    "/requests/{access_request_id}/decision",
    response_model=CandidateAccessRequestRead,
)
def decide_candidate_access_request(
    access_request_id: int,
    decision_data: CandidateAccessDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return update_candidate_access_decision(
            db,
            access_request_id=access_request_id,
            candidate_owner_user_id=current_user.id,
            decision=decision_data.decision,
        )

    except ValueError as exc:
        message = str(exc)

        if message == "Access request not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        )


@router.get(
    "/candidates/{candidate_id}",
    response_model=CandidateRecruiterRead,
)
def get_candidate_profile_for_organization(
    candidate_id: int,
    organization_id: int = Query(gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_verified_organization_role(
            ["company_admin", "recruiter"]
        )
    ),
):
    try:
        candidate = get_candidate_for_organization(
            db,
            candidate_id=candidate_id,
            organization_id=organization_id,
        )

        return candidate

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found or access not granted.",
        )

@router.get(
    "/candidates/{candidate_id}/cvs",
    response_model=list[CVDocumentRecruiterRead],
)
def get_candidate_approved_cvs_for_organization(
    candidate_id: int,
    organization_id: int = Query(gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_verified_organization_role(
            ["company_admin", "recruiter"]
        )
    ),
):
    try:
        # Confirm that this organization has been granted access.
        return get_approved_cvs_for_organization(
            db,
            candidate_id=candidate_id,
            organization_id=organization_id,
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found or access not granted.",
        )