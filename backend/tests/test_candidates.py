def test_create_candidate(client):
    response = client.post(
        "/api/v1/candidates",
        json={
            "full_name": "Test Candidate",
            "email": "test@example.com",
            "phone": "+230 50000000",
            "location": "Mauritius",
        },
    )

    assert response.status_code == 201
    assert response.json()["full_name"] == "Test Candidate"
    assert response.json()["email"] == "test@example.com"


def test_get_candidate(client):
    create_response = client.post(
        "/api/v1/candidates",
        json={
            "full_name": "Test Candidate",
            "email": "test@example.com",
        },
    )

    candidate_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/candidates/{candidate_id}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == candidate_id


def test_update_candidate(client):
    create_response = client.post(
        "/api/v1/candidates",
        json={
            "full_name": "Test Candidate",
            "email": "test@example.com",
            "location": "Mauritius",
        },
    )

    candidate_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/candidates/{candidate_id}",
        json={
            "professional_headline": "Python Backend Engineer",
        },
    )

    assert response.status_code == 200
    assert response.json()["professional_headline"] == "Python Backend Engineer"
    assert response.json()["location"] == "Mauritius"


def test_duplicate_email(client):
    candidate = {
        "full_name": "Test Candidate",
        "email": "test@example.com",
    }

    first_response = client.post(
        "/api/v1/candidates",
        json=candidate,
    )

    second_response = client.post(
        "/api/v1/candidates",
        json=candidate,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_candidate_not_found(client):
    response = client.get("/api/v1/candidates/9999")

    assert response.status_code == 404