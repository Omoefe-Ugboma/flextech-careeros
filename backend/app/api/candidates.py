from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Candidate, CVDocument

from fastapi import UploadFile, File

from app.models import CVDocument
from app.schemas.cv_document import CVDocumentRead
from app.services.cv.file_service import save_cv_file

from app.schemas.candidate import (
    CandidateCreate,
    CandidateRead,
    CandidateUpdate,
)

from app.services.cv.text_extractor import extract_cv_text
from app.services.cv.ai_extractor import extract_candidate_information
from datetime import datetime, timezone

from app.schemas.cv_extraction import CVExtraction
from sqlalchemy.exc import IntegrityError

router = APIRouter(
    prefix="/api/v1/candidates",
    tags=["Candidates"],
)


@router.post(
    "",
    response_model=CandidateRead,
    status_code=status.HTTP_201_CREATED,
)
def create_candidate(
    candidate_data: CandidateCreate,
    db: Session = Depends(get_db),
):
    candidate = Candidate(**candidate_data.model_dump())

    db.add(candidate)

    try:
        db.commit()
        db.refresh(candidate)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A candidate with this email already exists.",
        )

    return candidate


@router.get("/{candidate_id}", response_model=CandidateRead)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
):
    candidate = db.get(Candidate, candidate_id)

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found.",
        )

    return candidate


@router.put("/{candidate_id}", response_model=CandidateRead)
def update_candidate(
    candidate_id: int,
    candidate_data: CandidateUpdate,
    db: Session = Depends(get_db),
):
    candidate = db.get(Candidate, candidate_id)

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found.",
        )

    updates = candidate_data.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(candidate, field, value)

    try:
        db.commit()
        db.refresh(candidate)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A candidate with this email already exists.",
        )

    return candidate

@router.post(
    "/{candidate_id}/cv",
    response_model=CVDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_candidate_cv(
    candidate_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    candidate = db.get(Candidate, candidate_id)

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found.",
        )

    file_details = await save_cv_file(file)

    cv_document = CVDocument(
        candidate_id=candidate_id,
        original_filename=file_details["original_filename"],
        stored_filename=file_details["stored_filename"],
        file_path=file_details["file_path"],
        file_type=file_details["file_type"],
        file_size=file_details["file_size"],
        processing_status="uploaded",
    )

    try:
        db.add(cv_document)
        db.commit()
        db.refresh(cv_document)

    except Exception:
        db.rollback()

        from pathlib import Path

        Path(file_details["file_path"]).unlink(missing_ok=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save CV document.",
        )

    # Extract text from the uploaded document.
    
    
    # Stage 1: Extract text from the uploaded document.
    try:
        extracted_text = extract_cv_text(cv_document.file_path)

        if not extracted_text.strip():
            raise ValueError("No readable text was found in the CV.")

        cv_document.extracted_text = extracted_text
        cv_document.processing_status = "text_extracted"

        db.commit()

    except Exception:
        db.rollback()

        cv_document.processing_status = "failed"
        db.commit()
        db.refresh(cv_document)

        return cv_document


    # Stage 2: Extract structured candidate information using OpenAI.
    try:
        candidate_information = extract_candidate_information(
            cv_document.extracted_text
        )

        cv_document.extracted_data = candidate_information.model_dump(
            mode="json"
        )

        cv_document.processing_status = "processed"

    except Exception:
        cv_document.processing_status = "extraction_failed"

    db.commit()
    db.refresh(cv_document)

    return cv_document



@router.get(
    "/{candidate_id}/cv/{cv_document_id}",
    response_model=CVDocumentRead,
    status_code=status.HTTP_200_OK,
)
def get_candidate_cv(
    candidate_id: int,
    cv_document_id: int,
    db: Session = Depends(get_db),
):
    # 1. Confirm that the candidate exists.
    candidate = db.get(Candidate, candidate_id)

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found.",
        )

    # 2. Retrieve the CV belonging to this candidate.
    cv_document = db.scalar(
        select(CVDocument).where(
            CVDocument.id == cv_document_id,
            CVDocument.candidate_id == candidate_id,
        )
    )

    if cv_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV document not found for this candidate.",
        )

    # 3. Return the CV document and its review information.
    return cv_document



@router.post(
    "/{candidate_id}/cv/{cv_document_id}/approve",
    response_model=CVDocumentRead,
    status_code=status.HTTP_200_OK,
)
def approve_candidate_cv(
    candidate_id: int,
    cv_document_id: int,
    reviewed_data: CVExtraction,
    db: Session = Depends(get_db),
):
    # 1. Confirm that the candidate exists.
    candidate = db.get(Candidate, candidate_id)

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found.",
        )

    # 2. Find the CV belonging to this candidate.
    cv_document = db.scalar(
        select(CVDocument).where(
            CVDocument.id == cv_document_id,
            CVDocument.candidate_id == candidate_id,
        )
    )

    if cv_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV document not found for this candidate.",
        )

    # 3. Ensure AI extraction has completed.
    if cv_document.processing_status != "processed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CV processing must complete before approval.",
        )

    # 4. Prevent repeated approval.
    if cv_document.review_status != "pending_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This CV has already been reviewed.",
        )

    # 5. Preserve the original extraction and save reviewed data.
    cv_document.approved_data = reviewed_data.model_dump(
        mode="json"
    )

    # 6. Update the candidate's main profile.
    candidate_fields = [
        "full_name",
        "email",
        "phone",
        "location",
        "professional_headline",
        "professional_summary",
    ]

    for field in candidate_fields:
        value = getattr(reviewed_data, field)

        if value is not None:
            setattr(candidate, field, value)

    # 7. Record human approval.
    cv_document.review_status = "approved"
    cv_document.reviewed_at = datetime.now(timezone.utc)

    # 8. Save everything in one transaction.
    try:
        db.commit()
        db.refresh(cv_document)
        db.refresh(candidate)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The reviewed email address is already in use.",
        )

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not approve CV information.",
        )

    return cv_document
