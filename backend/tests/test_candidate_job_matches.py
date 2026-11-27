
from app.models import Candidate, CVDocument, JobDescription
from app.models.user import User


MATCH_ENDPOINT = "/api/v1/candidate-job-matches"


def create_matching_data(db, user_id):
    """Create a candidate, approved CV and processed job description."""

    candidate = Candidate(
        user_id=user_id,
        full_name="Test Candidate",
        email="candidate@example.com",
    )

    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    cv_document = CVDocument(
        candidate_id=candidate.id,
        original_filename="test_cv.pdf",
        stored_filename="test_cv_unique.pdf",
        file_path="storage/test_cv.pdf",
        file_type="pdf",
        file_size=1024,
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
            "work_experience": [],
            "projects": [],
        },
    )

    job = JobDescription(
        job_title="Python Backend Developer",
        company_name="Test Company",
        location="Mauritius",
        original_description=(
            "We require a Python developer with FastAPI "
            "and PostgreSQL experience."
        ),
        processing_status="processed",
        extracted_data={
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            "preferred_skills": ["React"],
            "qualifications": [
                "Bachelor's degree in Computer Science"
            ],
        },
    )

    db.add_all([cv_document, job])
    db.commit()

    db.refresh(cv_document)
    db.refresh(job)

    return candidate, cv_document, job


def test_matching_endpoint_rejects_unauthenticated_user(client):
    response = client.post(
        MATCH_ENDPOINT,
        json={
            "candidate_id": 1,
            "cv_document_id": 1,
            "job_description_id": 1,
        },
    )

    assert response.status_code == 401


def test_matching_endpoint_rejects_user_without_job_seeker_role(
    client,
    authenticated_client,
):
    _, headers = authenticated_client(
        email="company-admin@example.com",
        role="platform_admin",
    )

    response = client.post(
        MATCH_ENDPOINT,
        headers=headers,
        json={
            "candidate_id": 1,
            "cv_document_id": 1,
            "job_description_id": 1,
        },
    )

    assert response.status_code == 403


def test_matching_endpoint_rejects_another_users_candidate(
    client,
    test_db,
    authenticated_client,
):
    _, headers = authenticated_client(
        email="attacker@example.com",
        role="job_seeker",
    )

    owner = User(
        email="candidate-owner@example.com",
        hashed_password="test-password-hash",
        is_active=True,
        is_verified=True,
    )

    test_db.add(owner)
    test_db.commit()
    test_db.refresh(owner)

    candidate, cv_document, job = create_matching_data(
        test_db,
        owner.id,
    )

    response = client.post(
        MATCH_ENDPOINT,
        headers=headers,
        json={
            "candidate_id": candidate.id,
            "cv_document_id": cv_document.id,
            "job_description_id": job.id,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate not found."


def test_matching_endpoint_allows_job_seeker_to_match_own_candidate(
    client,
    test_db,
    authenticated_client,
):
    user, headers = authenticated_client(
        email="valid-jobseeker@example.com",
        role="job_seeker",
    )

    candidate, cv_document, job = create_matching_data(
        test_db,
        user.id,
    )

    response = client.post(
        MATCH_ENDPOINT,
        headers=headers,
        json={
            "candidate_id": candidate.id,
            "cv_document_id": cv_document.id,
            "job_description_id": job.id,
        },
    )

    assert response.status_code == 201

    result = response.json()

    assert result["candidate_id"] == candidate.id
    assert result["cv_document_id"] == cv_document.id
    assert result["job_description_id"] == job.id
    assert result["match_score"] is not None
    assert "scoring" in result["match_results"]
