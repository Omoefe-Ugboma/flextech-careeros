
from app.models import CVDocument


def create_candidate(client, headers, email="candidate@example.com"):
    response = client.post(
        "/api/v1/candidates",
        json={
            "full_name": "Test Candidate",
            "email": email,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_processed_cv(client, candidate_id, test_db):
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


def test_approve_cv_successfully(
    client, authenticated_client, test_db
):
    _, headers = authenticated_client()
    candidate_id = create_candidate(client, headers)

    cv_document_id = create_processed_cv(
        client, candidate_id, test_db
    )

    response = client.post(
        f"/api/v1/candidates/{candidate_id}/cv/{cv_document_id}/approve",
        json=approval_payload(),
        headers=headers,
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
    assert data["approved_data"]["full_name"] == "Test Candidate"


def test_cannot_approve_cv_twice(
    client, authenticated_client, test_db
):
    _, headers = authenticated_client()
    candidate_id = create_candidate(client, headers)

    cv_document_id = create_processed_cv(
        client, candidate_id, test_db
    )

    url = (
        f"/api/v1/candidates/{candidate_id}"
        f"/cv/{cv_document_id}/approve"
    )

    first_response = client.post(
        url, json=approval_payload(), headers=headers
    )
    second_response = client.post(
        url, json=approval_payload(), headers=headers
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409



def test_cannot_approve_another_candidates_cv(
    client, authenticated_client, test_db
):
    _, first_user_headers = authenticated_client(
        email="firstuser@example.com"
    )

    _, second_user_headers = authenticated_client(
        email="seconduser@example.com"
    )

    first_candidate_id = create_candidate(
        client, first_user_headers, "first@example.com"
    )

    second_candidate_id = create_candidate(
        client, second_user_headers, "second@example.com"
    )

    cv_document_id = create_processed_cv(
        client, first_candidate_id, test_db
    )

    response = client.post(
        f"/api/v1/candidates/{second_candidate_id}"
        f"/cv/{cv_document_id}/approve",
        json=approval_payload(),
        headers=second_user_headers,
    )

    assert response.status_code == 404




def test_unauthenticated_user_cannot_approve_cv(
    client, authenticated_client, test_db
):
    _, headers = authenticated_client()

    candidate_id = create_candidate(client, headers)

    cv_document_id = create_processed_cv(
        client, candidate_id, test_db
    )

    response = client.post(
        f"/api/v1/candidates/{candidate_id}"
        f"/cv/{cv_document_id}/approve",
        json=approval_payload(),
    )

    assert response.status_code == 401


def test_user_cannot_approve_another_users_cv(
    client, authenticated_client, test_db
):
    _, owner_headers = authenticated_client(
        email="approvalowner@example.com"
    )
    _, other_user_headers = authenticated_client(
        email="approvalother@example.com"
    )

    candidate_id = create_candidate(
        client,
        owner_headers,
        "approvalcandidate@example.com",
    )

    cv_document_id = create_processed_cv(
        client, candidate_id, test_db
    )

    response = client.post(
        f"/api/v1/candidates/{candidate_id}"
        f"/cv/{cv_document_id}/approve",
        json=approval_payload(),
        headers=other_user_headers,
    )

    assert response.status_code == 404


def test_cannot_approve_unprocessed_cv(
    client, authenticated_client, test_db
):
    _, headers = authenticated_client()
    candidate_id = create_candidate(client, headers)

    cv_document = CVDocument(
        candidate_id=candidate_id,
        original_filename="failed_cv.pdf",
        stored_filename="failed_cv_unique.pdf",
        file_path="storage/cvs/failed_cv.pdf",
        file_type="pdf",
        file_size=1024,
        processing_status="extraction_failed",
    )

    test_db.add(cv_document)
    test_db.commit()
    test_db.refresh(cv_document)

    response = client.post(
        f"/api/v1/candidates/{candidate_id}"
        f"/cv/{cv_document.id}/approve",
        json=approval_payload(),
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "CV processing must complete before approval."
    )


def test_approval_updates_candidate_profile(
    client, authenticated_client, test_db
):
    _, headers = authenticated_client()
    candidate_id = create_candidate(client, headers)

    cv_document_id = create_processed_cv(
        client, candidate_id, test_db
    )

    reviewed_data = approval_payload()
    reviewed_data["full_name"] = "Reviewed Candidate"
    reviewed_data["email"] = "reviewed@example.com"
    reviewed_data["professional_headline"] = (
        "Senior Python Backend Developer"
    )

    approval_response = client.post(
        f"/api/v1/candidates/{candidate_id}"
        f"/cv/{cv_document_id}/approve",
        json=reviewed_data,
        headers=headers,
    )

    assert approval_response.status_code == 200

    profile_response = client.get(
        f"/api/v1/candidates/{candidate_id}",
        headers=headers,
    )

    assert profile_response.status_code == 200

    profile = profile_response.json()

    assert profile["full_name"] == "Reviewed Candidate"
    assert profile["email"] == "reviewed@example.com"
    assert profile["professional_headline"] == (
        "Senior Python Backend Developer"
    )
    assert profile["phone"] == "+230 50000000"
    assert profile["location"] == "Mauritius"


def test_approve_cv_without_request_body(
    client, authenticated_client, test_db
):
    _, headers = authenticated_client()
    candidate_id = create_candidate(client, headers)

    cv_document_id = create_processed_cv(
        client, candidate_id, test_db
    )

    url = (
        f"/api/v1/candidates/{candidate_id}"
        f"/cv/{cv_document_id}/approve"
    )

    response = client.post(url, headers=headers)

    assert response.status_code == 200

    data = response.json()

    assert data["review_status"] == "approved"
    assert data["approved_data"]["full_name"] == "Test Candidate"
    assert data["approved_data"]["skills"] == ["Python"]
    assert data["extracted_data"]["full_name"] == "Test Candidate"
    assert data["extracted_data"]["skills"] == ["Python"]
    assert data["reviewed_at"] is not None


def test_cannot_approve_cv_with_empty_extracted_data(
    client, authenticated_client, test_db
):
    _, headers = authenticated_client()
    candidate_id = create_candidate(client, headers)

    cv_document = CVDocument(
        candidate_id=candidate_id,
        original_filename="empty_cv.pdf",
        stored_filename="empty_cv_unique.pdf",
        file_path="storage/cvs/empty_cv.pdf",
        file_type="pdf",
        file_size=1024,
        extracted_text="",
        extracted_data={},
        processing_status="processed",
    )

    test_db.add(cv_document)
    test_db.commit()
    test_db.refresh(cv_document)

    response = client.post(
        f"/api/v1/candidates/{candidate_id}"
        f"/cv/{cv_document.id}/approve",
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "No extracted CV information is available for approval."
    )


def test_cannot_approve_cv_with_invalid_extracted_data(
    client, authenticated_client, test_db
):
    _, headers = authenticated_client()
    candidate_id = create_candidate(client, headers)

    cv_document = CVDocument(
        candidate_id=candidate_id,
        original_filename="invalid_cv.pdf",
        stored_filename="invalid_cv_unique.pdf",
        file_path="storage/cvs/invalid_cv.pdf",
        file_type="pdf",
        file_size=1024,
        extracted_text="Invalid extracted information",
        extracted_data={
            "full_name": "Test Candidate",
            "skills": "Python",
        },
        processing_status="processed",
    )

    test_db.add(cv_document)
    test_db.commit()
    test_db.refresh(cv_document)

    response = client.post(
        f"/api/v1/candidates/{candidate_id}"
        f"/cv/{cv_document.id}/approve",
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Extracted CV information is invalid and cannot be approved."
    )
