
from unittest.mock import Mock

from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.schemas.job_description import JobDescriptionExtraction


JOB_DESCRIPTION_PAYLOAD = {
    "job_title": "Python Backend Developer",
    "company_name": "Example Technology Ltd",
    "location": "Port Louis, Mauritius",
    "original_description": (
        "We are seeking a Python Backend Developer to build APIs "
        "using Python and FastAPI. Required skills include Python, "
        "FastAPI, PostgreSQL, SQL, Git and Docker. Candidates should "
        "have at least three years of backend development experience. "
        "Experience with AWS and React is preferred."
    ),
}


def successful_extraction():
    return JobDescriptionExtraction(
        responsibilities=["Build and maintain APIs"],
        required_skills=[
            "Python",
            "FastAPI",
            "PostgreSQL",
            "SQL",
            "Git",
            "Docker",
        ],
        preferred_skills=["AWS", "React"],
        qualifications=["Backend development experience"],
        experience_requirement=(
            "at least three years of backend development experience"
        ),
        employment_type="full-time",
    )


def create_verified_company_member(
    authenticated_client,
    test_db,
    email="admin@example.com",
    role="company_admin",
    membership_status="active",
    is_active=True,
    is_verified=True,
):
    user, headers = authenticated_client(email=email)

    organization = Organization(
        name=f"{email.split('@')[0]} Company",
        company_email=f"{email.split('@')[0]}-company@example.com",
        is_active=is_active,
        is_verified=is_verified,
    )

    test_db.add(organization)
    test_db.flush()

    membership = OrganizationMembership(
        user_id=user.id,
        organization_id=organization.id,
        role=role,
        membership_status=membership_status,
    )

    test_db.add(membership)
    test_db.commit()

    return organization, headers


def create_job(
    client,
    headers,
    organization_id,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.api.job_descriptions.extract_job_requirements",
        Mock(return_value=successful_extraction()),
    )

    return client.post(
        "/api/v1/job-descriptions",
        params={"organization_id": organization_id},
        json=JOB_DESCRIPTION_PAYLOAD,
        headers=headers,
    )


def test_create_job_description_success(
    client,
    test_db,
    authenticated_client,
    monkeypatch,
):
    organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
    )

    mock_extractor = Mock(return_value=successful_extraction())

    monkeypatch.setattr(
        "app.api.job_descriptions.extract_job_requirements",
        mock_extractor,
    )

    response = client.post(
        "/api/v1/job-descriptions",
        params={"organization_id": organization.id},
        json=JOB_DESCRIPTION_PAYLOAD,
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["job_title"] == "Python Backend Developer"
    assert data["company_name"] == organization.name
    assert data["processing_status"] == "processed"

    assert "Python" in data["extracted_data"]["required_skills"]
    assert "AWS" in data["extracted_data"]["preferred_skills"]

    assert data["extracted_data"]["experience_requirement"] == (
        "at least three years of backend development experience"
    )

    mock_extractor.assert_called_once()


def test_extraction_failure_preserves_job_description(
    client,
    test_db,
    authenticated_client,
    monkeypatch,
):
    organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
    )

    mock_extractor = Mock(
        side_effect=RuntimeError("OpenAI service unavailable")
    )

    monkeypatch.setattr(
        "app.api.job_descriptions.extract_job_requirements",
        mock_extractor,
    )

    response = client.post(
        "/api/v1/job-descriptions",
        params={"organization_id": organization.id},
        json=JOB_DESCRIPTION_PAYLOAD,
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["job_title"] == "Python Backend Developer"
    assert data["original_description"] == (
        JOB_DESCRIPTION_PAYLOAD["original_description"]
    )
    assert data["processing_status"] == "extraction_failed"
    assert data["extracted_data"] is None


def test_get_job_description(
    client,
    test_db,
    authenticated_client,
    monkeypatch,
):
    organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
    )

    create_response = create_job(
        client,
        headers,
        organization.id,
        monkeypatch,
    )

    assert create_response.status_code == 201
    job_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/job-descriptions/{job_id}",
        params={"organization_id": organization.id},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == job_id
    assert response.json()["job_title"] == "Python Backend Developer"


def test_list_job_descriptions(
    client,
    test_db,
    authenticated_client,
    monkeypatch,
):
    organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
    )

    create_response = create_job(
        client,
        headers,
        organization.id,
        monkeypatch,
    )

    assert create_response.status_code == 201

    response = client.get(
        "/api/v1/job-descriptions",
        params={"organization_id": organization.id},
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["job_title"] == "Python Backend Developer"


def test_get_missing_job_description_returns_404(
    client,
    test_db,
    authenticated_client,
):
    organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
    )

    response = client.get(
        "/api/v1/job-descriptions/99999",
        params={"organization_id": organization.id},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job description not found."


def test_recruiter_can_create_job_description(
    client,
    test_db,
    authenticated_client,
    monkeypatch,
):
    organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="recruiter@example.com",
        role="recruiter",
    )

    response = create_job(
        client,
        headers,
        organization.id,
        monkeypatch,
    )

    assert response.status_code == 201
    assert response.json()["company_name"] == organization.name


def test_company_cannot_access_another_company_job(
    client,
    test_db,
    authenticated_client,
    monkeypatch,
):
    organization_a, headers_a = create_verified_company_member(
        authenticated_client,
        test_db,
        email="companya@example.com",
    )

    organization_b, headers_b = create_verified_company_member(
        authenticated_client,
        test_db,
        email="companyb@example.com",
    )

    create_response = create_job(
        client,
        headers_b,
        organization_b.id,
        monkeypatch,
    )

    assert create_response.status_code == 201
    job_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/job-descriptions/{job_id}",
        params={"organization_id": organization_a.id},
        headers=headers_a,
    )

    assert response.status_code == 404


def test_company_can_only_list_its_own_jobs(
    client,
    test_db,
    authenticated_client,
    monkeypatch,
):
    organization_a, headers_a = create_verified_company_member(
        authenticated_client,
        test_db,
        email="listcompanya@example.com",
    )

    organization_b, headers_b = create_verified_company_member(
        authenticated_client,
        test_db,
        email="listcompanyb@example.com",
    )

    response_a = create_job(
        client,
        headers_a,
        organization_a.id,
        monkeypatch,
    )

    response_b = create_job(
        client,
        headers_b,
        organization_b.id,
        monkeypatch,
    )

    assert response_a.status_code == 201
    assert response_b.status_code == 201

    response = client.get(
        "/api/v1/job-descriptions",
        params={"organization_id": organization_a.id},
        headers=headers_a,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["company_name"] == organization_a.name


def test_pending_membership_cannot_create_job(
    client,
    test_db,
    authenticated_client,
):
    organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="pending@example.com",
        membership_status="pending",
    )

    response = client.post(
        "/api/v1/job-descriptions",
        params={"organization_id": organization.id},
        json=JOB_DESCRIPTION_PAYLOAD,
        headers=headers,
    )

    assert response.status_code == 403


def test_suspended_membership_cannot_create_job(
    client,
    test_db,
    authenticated_client,
):
    organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="suspended@example.com",
        membership_status="suspended",
    )

    response = client.post(
        "/api/v1/job-descriptions",
        params={"organization_id": organization.id},
        json=JOB_DESCRIPTION_PAYLOAD,
        headers=headers,
    )

    assert response.status_code == 403


def test_unverified_organization_cannot_create_job(
    client,
    test_db,
    authenticated_client,
):
    organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="unverified@example.com",
        is_verified=False,
    )

    response = client.post(
        "/api/v1/job-descriptions",
        params={"organization_id": organization.id},
        json=JOB_DESCRIPTION_PAYLOAD,
        headers=headers,
    )

    assert response.status_code == 403


def test_inactive_organization_cannot_create_job(
    client,
    test_db,
    authenticated_client,
):
    organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="inactive@example.com",
        is_active=False,
    )

    response = client.post(
        "/api/v1/job-descriptions",
        params={"organization_id": organization.id},
        json=JOB_DESCRIPTION_PAYLOAD,
        headers=headers,
    )

    assert response.status_code == 403


def test_unauthenticated_user_cannot_list_jobs(
    client,
    test_db,
    authenticated_client,
):
    organization, _ = create_verified_company_member(
        authenticated_client,
        test_db,
        email="privatecompany@example.com",
    )

    response = client.get(
        "/api/v1/job-descriptions",
        params={"organization_id": organization.id},
    )

    assert response.status_code == 401
