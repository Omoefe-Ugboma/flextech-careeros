from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Candidate

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
