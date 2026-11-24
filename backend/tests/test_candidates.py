
from types import SimpleNamespace

import app.api.candidates as candidates_api
from app.models.candidate import Candidate


def test_create_candidate(client, authenticated_client, test_db):
    user, headers = authenticated_client()

    response = client.post(
        "/api/v1/candidates",
        json={
            "full_name": "Test Candidate",
            "email": "test@example.com",
            "phone": "+230 50000000",
            "location": "Mauritius",
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["full_name"] == "Test Candidate"
    assert response.json()["email"] == "test@example.com"

    candidate = test_db.query(Candidate).filter_by(
        email="test@example.com"
    ).first()

    assert candidate is not None
    assert candidate.user_id == user.id


def test_create_candidate_rejects_unauthenticated_user(client):
    response = client.post(
        "/api/v1/candidates",
        json={
            "full_name": "Test Candidate",
            "email": "test@example.com",
        },
    )

    assert response.status_code == 401


def test_get_candidate(client, authenticated_client):
    _, headers = authenticated_client()

    create_response = client.post(
        "/api/v1/candidates",
        json={
            "full_name": "Test Candidate",
            "email": "test@example.com",
        },
        headers=headers,
    )

    candidate_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/candidates/{candidate_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == candidate_id


def test_update_candidate(client, authenticated_client):
    _, headers = authenticated_client()

    create_response = client.post(
        "/api/v1/candidates",
        json={
            "full_name": "Test Candidate",
            "email": "test@example.com",
            "location": "Mauritius",
        },
        headers=headers,
    )

    candidate_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/candidates/{candidate_id}",
        json={
            "professional_headline": "Python Backend Engineer",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["professional_headline"] == "Python Backend Engineer"
    assert response.json()["location"] == "Mauritius"


def test_duplicate_email(client, authenticated_client):
    _, headers = authenticated_client()

    candidate = {
        "full_name": "Test Candidate",
        "email": "test@example.com",
    }

    first_response = client.post(
        "/api/v1/candidates",
        json=candidate,
        headers=headers,
    )

    second_response = client.post(
        "/api/v1/candidates",
        json=candidate,
        headers=headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_candidate_not_found(client, authenticated_client):
    _, headers = authenticated_client()

    response = client.get(
        "/api/v1/candidates/9999",
        headers=headers,
    )

    assert response.status_code == 404


def test_user_cannot_view_another_users_candidate(
    client,
    authenticated_client,
):
    _, owner_headers = authenticated_client(
        email="owner@example.com"
    )

    _, other_user_headers = authenticated_client(
        email="otheruser@example.com"
    )

    create_response = client.post(
        "/api/v1/candidates",
        json={
            "full_name": "Private Candidate",
            "email": "private@example.com",
        },
        headers=owner_headers,
    )

    candidate_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/candidates/{candidate_id}",
        headers=other_user_headers,
    )

    assert response.status_code == 404


def test_user_cannot_update_another_users_candidate(
    client,
    authenticated_client,
    test_db,
):
    _, owner_headers = authenticated_client(
        email="owner2@example.com"
    )

    _, other_user_headers = authenticated_client(
        email="otheruser2@example.com"
    )

    create_response = client.post(
        "/api/v1/candidates",
        json={
            "full_name": "Private Candidate",
            "email": "private2@example.com",
        },
        headers=owner_headers,
    )

    candidate_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/candidates/{candidate_id}",
        json={
            "professional_headline": "Unauthorized Update",
        },
        headers=other_user_headers,
    )

    assert response.status_code == 404

    candidate = test_db.get(Candidate, candidate_id)

    assert candidate.professional_headline is None


def test_candidate_owner_can_upload_cv(
    client,
    authenticated_client,
    monkeypatch,
    tmp_path,
):
    _, headers = authenticated_client()

    create_response = client.post(
        "/api/v1/candidates",
        json={
            "full_name": "CV Owner",
            "email": "cvowner@example.com",
        },
        headers=headers,
    )

    candidate_id = create_response.json()["id"]

    cv_path = tmp_path / "test_cv.pdf"
    cv_path.write_bytes(b"test pdf content")

    async def mock_save_cv_file(file):
        return {
            "original_filename": "test_cv.pdf",
            "stored_filename": "test_cv_unique.pdf",
            "file_path": str(cv_path),
            "file_type": "pdf",
            "file_size": 1024,
        }

    monkeypatch.setattr(
        candidates_api,
        "save_cv_file",
        mock_save_cv_file,
    )

    monkeypatch.setattr(
        candidates_api,
        "extract_cv_text",
        lambda path: "Test candidate CV",
    )

    monkeypatch.setattr(
        candidates_api,
        "extract_candidate_information",
        lambda text: SimpleNamespace(
            model_dump=lambda mode: {}
        ),
    )

    response = client.post(
        f"/api/v1/candidates/{candidate_id}/cv",
        files={
            "file": (
                "test_cv.pdf",
                b"test pdf content",
                "application/pdf",
            )
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["processing_status"] == "processed"


def test_unauthenticated_user_cannot_upload_cv(client):
    response = client.post(
        "/api/v1/candidates/1/cv",
        files={
            "file": (
                "test_cv.pdf",
                b"test pdf content",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 401


def test_user_cannot_upload_cv_to_another_users_candidate(
    client,
    authenticated_client,
):
    _, owner_headers = authenticated_client(
        email="cvowner2@example.com"
    )

    _, other_user_headers = authenticated_client(
        email="othercvuser@example.com"
    )

    create_response = client.post(
        "/api/v1/candidates",
        json={
            "full_name": "Private CV Owner",
            "email": "privatecv@example.com",
        },
        headers=owner_headers,
    )

    candidate_id = create_response.json()["id"]

    response = client.post(
        f"/api/v1/candidates/{candidate_id}/cv",
        files={
            "file": (
                "test_cv.pdf",
                b"test pdf content",
                "application/pdf",
            )
        },
        headers=other_user_headers,
    )

    assert response.status_code == 404



def create_candidate_with_cv(
    client,
    headers,
    monkeypatch,
    tmp_path,
    email,
):
    create_response = client.post(
        "/api/v1/candidates",
        json={
            "full_name": "CV Test Candidate",
            "email": email,
        },
        headers=headers,
    )

    assert create_response.status_code == 201
    candidate_id = create_response.json()["id"]

    cv_path = tmp_path / "test_retrieval_cv.pdf"
    cv_path.write_bytes(b"test pdf content")

    async def mock_save_cv_file(file):
        return {
            "original_filename": "test_retrieval_cv.pdf",
            "stored_filename": "test_retrieval_cv_unique.pdf",
            "file_path": str(cv_path),
            "file_type": "pdf",
            "file_size": 1024,
        }

    monkeypatch.setattr(
        candidates_api,
        "save_cv_file",
        mock_save_cv_file,
    )

    monkeypatch.setattr(
        candidates_api,
        "extract_cv_text",
        lambda path: "Test candidate CV",
    )

    monkeypatch.setattr(
        candidates_api,
        "extract_candidate_information",
        lambda text: SimpleNamespace(
            model_dump=lambda mode: {}
        ),
    )

    upload_response = client.post(
        f"/api/v1/candidates/{candidate_id}/cv",
        files={
            "file": (
                "test_retrieval_cv.pdf",
                b"test pdf content",
                "application/pdf",
            )
        },
        headers=headers,
    )

    assert upload_response.status_code == 201

    cv_document_id = upload_response.json()["id"]

    return candidate_id, cv_document_id


def test_candidate_owner_can_retrieve_cv(
    client,
    authenticated_client,
    monkeypatch,
    tmp_path,
):
    _, headers = authenticated_client(
        email="retrieveowner@example.com"
    )

    candidate_id, cv_document_id = create_candidate_with_cv(
        client,
        headers,
        monkeypatch,
        tmp_path,
        "retrieveowner@example.com",
    )

    response = client.get(
        f"/api/v1/candidates/{candidate_id}/cv/{cv_document_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == cv_document_id


def test_unauthenticated_user_cannot_retrieve_cv(
    client,
    authenticated_client,
    monkeypatch,
    tmp_path,
):
    _, owner_headers = authenticated_client(
        email="unauthretrieve@example.com"
    )

    candidate_id, cv_document_id = create_candidate_with_cv(
        client,
        owner_headers,
        monkeypatch,
        tmp_path,
        "unauthretrieve@example.com",
    )

    response = client.get(
        f"/api/v1/candidates/{candidate_id}/cv/{cv_document_id}",
    )

    assert response.status_code == 401


def test_user_cannot_retrieve_another_users_cv(
    client,
    authenticated_client,
    monkeypatch,
    tmp_path,
):
    _, owner_headers = authenticated_client(
        email="cvretrieveowner@example.com"
    )

    _, other_user_headers = authenticated_client(
        email="cvretrieveother@example.com"
    )

    candidate_id, cv_document_id = create_candidate_with_cv(
        client,
        owner_headers,
        monkeypatch,
        tmp_path,
        "cvretrieveowner@example.com",
    )

    response = client.get(
        f"/api/v1/candidates/{candidate_id}/cv/{cv_document_id}",
        headers=other_user_headers,
    )

    assert response.status_code == 404
