
from unittest.mock import Mock

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
        responsibilities=[
            "Build and maintain APIs",
        ],
        required_skills=[
            "Python",
            "FastAPI",
            "PostgreSQL",
            "SQL",
            "Git",
            "Docker",
        ],
        preferred_skills=[
            "AWS",
            "React",
        ],
        qualifications=[
            "Backend development experience",
        ],
        experience_requirement=(
            "at least three years of backend development experience"
        ),
        employment_type="full-time",
    )


def test_create_job_description_success(client, monkeypatch):
    mock_extractor = Mock(
        return_value=successful_extraction()
    )

    monkeypatch.setattr(
        "app.api.job_descriptions.extract_job_requirements",
        mock_extractor,
    )

    response = client.post(
        "/api/v1/job-descriptions",
        json=JOB_DESCRIPTION_PAYLOAD,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["job_title"] == "Python Backend Developer"
    assert data["company_name"] == "Example Technology Ltd"
    assert data["processing_status"] == "processed"

    assert "Python" in data["extracted_data"]["required_skills"]
    assert "AWS" in data["extracted_data"]["preferred_skills"]

    assert data["extracted_data"]["experience_requirement"] == (
        "at least three years of backend development experience"
    )

    mock_extractor.assert_called_once()


def test_extraction_failure_preserves_job_description(
    client,
    monkeypatch,
):
    mock_extractor = Mock(
        side_effect=RuntimeError("OpenAI service unavailable")
    )

    monkeypatch.setattr(
        "app.api.job_descriptions.extract_job_requirements",
        mock_extractor,
    )

    response = client.post(
        "/api/v1/job-descriptions",
        json=JOB_DESCRIPTION_PAYLOAD,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["job_title"] == "Python Backend Developer"

    assert data["original_description"] == (
        JOB_DESCRIPTION_PAYLOAD["original_description"]
    )

    assert data["processing_status"] == "extraction_failed"
    assert data["extracted_data"] is None


def test_get_job_description(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.job_descriptions.extract_job_requirements",
        Mock(return_value=successful_extraction()),
    )

    create_response = client.post(
        "/api/v1/job-descriptions",
        json=JOB_DESCRIPTION_PAYLOAD,
    )

    job_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/job-descriptions/{job_id}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == job_id
    assert response.json()["job_title"] == "Python Backend Developer"


def test_list_job_descriptions(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.job_descriptions.extract_job_requirements",
        Mock(return_value=successful_extraction()),
    )

    client.post(
        "/api/v1/job-descriptions",
        json=JOB_DESCRIPTION_PAYLOAD,
    )

    response = client.get("/api/v1/job-descriptions")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["job_title"] == "Python Backend Developer"


def test_get_missing_job_description_returns_404(client):
    response = client.get(
        "/api/v1/job-descriptions/99999"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job description not found."
