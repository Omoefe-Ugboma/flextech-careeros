from app.models import CVDocument

def create_candidate(client, email="candidate@example.com"):
    response = client.post(
        "/api/v1/candidates",
        json={
            "full_name": "Test Candidate",
            "email": email,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]



def create_processed_cv(client, candidate_id, test_db):
    from app.models import CVDocument

    cv_document = CVDocument(
        candidate_id=candidate_id,
        original_filename="test_cv.pdf",
        stored_filename="test_cv_unique.pdf",
        file_path="storage/cvs/test_cv.pdf",
        file_type="pdf",
        file_size=1024,
        extracted_text="Test candidate CV",
        extracted_data={
            "full_name": "Test Candidate",
            "skills": ["Python"],
        },
        processing_status="processed",
    )

    test_db.add(cv_document)
    test_db.commit()
    test_db.refresh(cv_document)

    return cv_document.id



def approval_payload():
    return {
        "full_name": "Test Candidate",
        "email": "candidate@example.com",
        "phone": "+230 50000000",
        "location": "Mauritius",
        "professional_headline": "Python Backend Developer",
        "professional_summary": "Experienced backend developer.",
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "education": [],
        "work_experience": [],
        "projects": [],
        "certifications": [],
    }


def test_approve_cv_successfully(client, test_db):
    candidate_id = create_candidate(client)
    cv_document_id = create_processed_cv(
    client,
    candidate_id,
    test_db,
)

    response = client.post(
        f"/api/v1/candidates/{candidate_id}/cv/{cv_document_id}/approve",
        json=approval_payload(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["review_status"] == "approved"
    assert data["approved_data"]["skills"] == [
        "Python",
        "FastAPI",
        "PostgreSQL",
    ]
    assert data["extracted_data"]["skills"] == ["Python"]
    assert data["reviewed_at"] is not None
    
    assert data["extracted_data"]["full_name"] == "Test Candidate"
    assert data["extracted_data"]["skills"] == ["Python"]

    assert data["approved_data"]["full_name"] == "Test Candidate"
    assert data["approved_data"]["skills"] == [
        "Python",
        "FastAPI",
        "PostgreSQL",
    ]


def test_cannot_approve_cv_twice(client, test_db):
    candidate_id = create_candidate(client)

    cv_document_id = create_processed_cv(
        client,
        candidate_id,
        test_db,
    )

    url = (
        f"/api/v1/candidates/{candidate_id}"
        f"/cv/{cv_document_id}/approve"
    )

    first_response = client.post(url, json=approval_payload())
    second_response = client.post(url, json=approval_payload())

    assert first_response.status_code == 200
    assert second_response.status_code == 409


def test_cannot_approve_another_candidates_cv(client, test_db):
    first_candidate_id = create_candidate(
        client,
        "first@example.com",
    )
    second_candidate_id = create_candidate(
        client,
        "second@example.com",
    )

    cv_document_id = create_processed_cv(
        client,
        first_candidate_id,
        test_db,
    )

    response = client.post(
        f"/api/v1/candidates/{second_candidate_id}"
        f"/cv/{cv_document_id}/approve",
        json=approval_payload(),
    )

    assert response.status_code == 404



def test_cannot_approve_unprocessed_cv(client, test_db):
    from app.models import CVDocument

    candidate_id = create_candidate(client)

    # Create a CV document that has failed AI extraction.
    cv_document = CVDocument(
        candidate_id=candidate_id,
        original_filename="failed_cv.pdf",
        stored_filename="failed_cv_unique.pdf",
        file_path="storage/cvs/failed_cv.pdf",
        file_type="pdf",
        file_size=1024,
        processing_status="extraction_failed",
    )

    # Save the test CV in the temporary SQLite database.
    test_db.add(cv_document)
    test_db.commit()
    test_db.refresh(cv_document)

    cv_document_id = cv_document.id

    # Attempt to approve a CV that has not been processed.
    response = client.post(
        f"/api/v1/candidates/{candidate_id}"
        f"/cv/{cv_document_id}/approve",
        json=approval_payload(),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "CV processing must complete before approval."
    )




def test_approval_updates_candidate_profile(client, test_db):
    candidate_id = create_candidate(client)

    cv_document_id = create_processed_cv(
        client,
        candidate_id,
        test_db,
    )

    # Prepare corrected information supplied by the candidate.
    reviewed_data = approval_payload()
    reviewed_data["full_name"] = "Reviewed Candidate"
    reviewed_data["email"] = "reviewed@example.com"
    reviewed_data["professional_headline"] = (
        "Senior Python Backend Developer"
    )

    # Approve the reviewed CV.
    approval_response = client.post(
        f"/api/v1/candidates/{candidate_id}"
        f"/cv/{cv_document_id}/approve",
        json=reviewed_data,
    )

    assert approval_response.status_code == 200

    # Retrieve the candidate's main profile.
    profile_response = client.get(
        f"/api/v1/candidates/{candidate_id}"
    )

    assert profile_response.status_code == 200

    profile = profile_response.json()

    # Verify that approved information updated the profile.
    assert profile["full_name"] == "Reviewed Candidate"
    assert profile["email"] == "reviewed@example.com"
    assert profile["professional_headline"] == (
        "Senior Python Backend Developer"
    )
    assert profile["phone"] == "+230 50000000"
    assert profile["location"] == "Mauritius"
