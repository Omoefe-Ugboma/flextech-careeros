import pytest
from fastapi import HTTPException

from app.models import (
    Candidate,
    CVDocument,
    JobDescription,
    CandidateJobMatch,
)

from app.services.matching.match_service import (
    get_approved_cv,
    get_processed_job_description,
    run_candidate_job_match,
)

def create_candidate(db, email="candidate@example.com"):
    candidate = Candidate(
        full_name="Test Candidate",
        email=email,
    )

    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    return candidate


def create_cv(
    db,
    candidate_id,
    processing_status="processed",
    review_status="approved",
    approved_data=None,
):
    cv_document = CVDocument(
        candidate_id=candidate_id,
        original_filename="test_cv.pdf",
        stored_filename="test_cv_unique.pdf",
        file_path="storage/test_cv.pdf",
        file_type="pdf",
        file_size=1024,
        processing_status=processing_status,
        review_status=review_status,
                approved_data=(
            approved_data
            if approved_data is not None
            else {
                "full_name": "Test Candidate",
                "skills": ["Python", "FastAPI"],
                "education": [],
            }
        ),
    )

    db.add(cv_document)
    db.commit()
    db.refresh(cv_document)

    return cv_document


def test_get_approved_cv_candidate_not_found(test_db):
    with pytest.raises(HTTPException) as exc_info:
        get_approved_cv(
            db=test_db,
            candidate_id=999,
            cv_document_id=1,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Candidate not found."
    

def test_get_approved_cv_document_not_found(test_db):
    candidate = create_candidate(test_db)

    with pytest.raises(HTTPException) as exc_info:
        get_approved_cv(
            db=test_db,
            candidate_id=candidate.id,
            cv_document_id=999,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == (
        "CV document not found for this candidate."
    )
    

def test_get_approved_cv_rejects_another_candidates_cv(test_db):
    candidate_one = create_candidate(
        test_db,
        email="candidate1@example.com",
    )

    candidate_two = create_candidate(
        test_db,
        email="candidate2@example.com",
    )

    cv_document = create_cv(
        test_db,
        candidate_id=candidate_one.id,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_approved_cv(
            db=test_db,
            candidate_id=candidate_two.id,
            cv_document_id=cv_document.id,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == (
        "CV document not found for this candidate."
    )
    

def test_get_approved_cv_rejects_unprocessed_cv(test_db):
    candidate = create_candidate(test_db)

    cv_document = create_cv(
        test_db,
        candidate_id=candidate.id,
        processing_status="extraction_failed",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_approved_cv(
            db=test_db,
            candidate_id=candidate.id,
            cv_document_id=cv_document.id,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == (
        "CV document has not been processed successfully."
    )
    

def test_get_approved_cv_rejects_pending_review(test_db):
    candidate = create_candidate(test_db)

    cv_document = create_cv(
        test_db,
        candidate_id=candidate.id,
        processing_status="processed",
        review_status="pending_review",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_approved_cv(
            db=test_db,
            candidate_id=candidate.id,
            cv_document_id=cv_document.id,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == (
        "CV document has not been approved or contains no approved data."
    )
    
def test_get_approved_cv_rejects_empty_approved_data(test_db):
    candidate = create_candidate(test_db)

    cv_document = create_cv(
        test_db,
        candidate_id=candidate.id,
        processing_status="processed",
        review_status="approved",
        approved_data={},
    )

    with pytest.raises(HTTPException) as exc_info:
        get_approved_cv(
            db=test_db,
            candidate_id=candidate.id,
            cv_document_id=cv_document.id,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == (
        "CV document has not been approved or contains no approved data."
    )
    

def test_get_approved_cv_returns_valid_cv(test_db):
    candidate = create_candidate(test_db)

    cv_document = create_cv(
        test_db,
        candidate_id=candidate.id,
        processing_status="processed",
        review_status="approved",
        approved_data={
            "full_name": "Test Candidate",
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "education": [
                {
                    "qualification": "Bachelor's degree",
                    "field_of_study": "Computer Science",
                }
            ],
        },
    )

    result = get_approved_cv(
        db=test_db,
        candidate_id=candidate.id,
        cv_document_id=cv_document.id,
    )

    assert result.id == cv_document.id
    assert result.candidate_id == candidate.id
    assert result.review_status == "approved"
    assert result.processing_status == "processed"
    assert result.approved_data["skills"] == [
        "Python",
        "FastAPI",
        "PostgreSQL",
    ]

def create_job_description(
    db,
    processing_status="processed",
    extracted_data=None,
):
    job = JobDescription(
        job_title="Python Backend Developer",
        company_name="Test Company",
        location="Mauritius",
        original_description=(
            "We require a Python developer with FastAPI "
            "and PostgreSQL experience."
        ),
        processing_status=processing_status,
        extracted_data=(
            extracted_data
            if extracted_data is not None
            else {
                "required_skills": ["Python", "FastAPI"],
                "preferred_skills": ["React"],
                "qualifications": [],
            }
        ),
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job

def test_get_processed_job_description_not_found(test_db):
    with pytest.raises(HTTPException) as exc:
        get_processed_job_description(test_db, 999)

    assert exc.value.status_code == 404


def test_get_processed_job_description_rejects_failed_extraction(test_db):
    job = create_job_description(
        test_db,
        processing_status="extraction_failed",
    )

    with pytest.raises(HTTPException) as exc:
        get_processed_job_description(test_db, job.id)

    assert exc.value.status_code == 409


def test_get_processed_job_description_rejects_empty_extracted_data(test_db):
    job = create_job_description(
        test_db,
        extracted_data={},
    )

    with pytest.raises(HTTPException) as exc:
        get_processed_job_description(test_db, job.id)

    assert exc.value.status_code == 409


def test_get_processed_job_description_returns_valid_job(test_db):
    job = create_job_description(test_db)

    result = get_processed_job_description(test_db, job.id)

    assert result.id == job.id
    assert result.processing_status == "processed"
    assert result.extracted_data["required_skills"] == [
        "Python",
        "FastAPI",
    ]

def test_run_candidate_job_match_saves_match_record(test_db):
    candidate = create_candidate(test_db)

    cv_document = create_cv(
        test_db,
        candidate_id=candidate.id,
        approved_data={
            "full_name": "Test Candidate",
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "education": [
                {
                    "qualification": "Bachelor's degree",
                    "field_of_study": "Computer Science",
                }
            ],
            "projects": [],
        },
    )

    job = create_job_description(
        test_db,
        extracted_data={
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            "preferred_skills": ["React"],
            "qualifications": ["Bachelor's degree in Computer Science"],
        },
    )

    result = run_candidate_job_match(
        db=test_db,
        candidate_id=candidate.id,
        cv_document_id=cv_document.id,
        job_description_id=job.id,
    )

    saved_match = test_db.get(CandidateJobMatch, result["id"])

    assert saved_match is not None
    assert saved_match.candidate_id == candidate.id
    assert saved_match.cv_document_id == cv_document.id
    assert saved_match.job_description_id == job.id
    assert saved_match.match_score == 100.0
    assert result["match_results"]["qualifications"]["status"] == "met"