
from sqlalchemy import select
from datetime import datetime, timezone
from app.models.candidate import Candidate
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.candidate_organization_access import (
    CandidateOrganizationAccess,
)
from app.models.candidate_access_audit_event import (
    CandidateAccessAuditEvent,
)

from app.models.cv_document import CVDocument

def create_verified_company_member(
    authenticated_client,
    test_db,
    email="recruiter@example.com",
    role="recruiter",
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

    return user, organization, headers



def create_candidate(
    test_db,
    user_id=None,
    email="candidate@example.com",
):
    candidate = Candidate(
        user_id=user_id,
        full_name="Test Candidate",
        email=email,
    )

    test_db.add(candidate)
    test_db.commit()
    test_db.refresh(candidate)

    return candidate



def test_recruiter_can_request_candidate_access(
    client,
    test_db,
    authenticated_client,
):
    user, organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="recruiter@example.com",
        role="recruiter",
    )

    candidate_user, _ = authenticated_client(
        email="candidate@example.com",
    )

    candidate = create_candidate(
        test_db,
        user_id=candidate_user.id,
    )

    response = client.post(
        "/api/v1/candidate-access/requests",
        params={"organization_id": organization.id},
        json={"candidate_id": candidate.id},
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["candidate_id"] == candidate.id
    assert data["organization_id"] == organization.id
    assert data["requested_by_user_id"] == user.id
    assert data["access_status"] == "pending"

    access_record = test_db.scalar(
        select(CandidateOrganizationAccess).where(
            CandidateOrganizationAccess.candidate_id == candidate.id,
            CandidateOrganizationAccess.organization_id == organization.id,
        )
    )

    assert access_record is not None
    assert access_record.access_status == "pending"

    audit_event = test_db.scalar(
        select(CandidateAccessAuditEvent).where(
            CandidateAccessAuditEvent.candidate_id_snapshot == candidate.id,
            CandidateAccessAuditEvent.organization_id_snapshot == organization.id,
        )
    )

    assert audit_event is not None
    assert audit_event.event_type == "requested"
    assert audit_event.new_status == "pending"
    assert audit_event.actor_user_id_snapshot == user.id


def test_duplicate_pending_access_request_returns_conflict(
    client,
    test_db,
    authenticated_client,
):
    _, organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="duplicate-recruiter@example.com",
        role="recruiter",
    )

    candidate_user, _ = authenticated_client(
        email="duplicate-candidate@example.com",
    )

    candidate = create_candidate(
        test_db,
        user_id=candidate_user.id,
    )

    payload = {"candidate_id": candidate.id}
    params = {"organization_id": organization.id}

    first_response = client.post(
        "/api/v1/candidate-access/requests",
        params=params,
        json=payload,
        headers=headers,
    )

    second_response = client.post(
        "/api/v1/candidate-access/requests",
        params=params,
        json=payload,
        headers=headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

    access_records = test_db.scalars(
        select(CandidateOrganizationAccess).where(
            CandidateOrganizationAccess.candidate_id == candidate.id,
            CandidateOrganizationAccess.organization_id == organization.id,
        )
    ).all()

    audit_events = test_db.scalars(
        select(CandidateAccessAuditEvent).where(
            CandidateAccessAuditEvent.candidate_id_snapshot == candidate.id,
            CandidateAccessAuditEvent.organization_id_snapshot == organization.id,
        )
    ).all()

    assert len(access_records) == 1
    assert len(audit_events) == 1


def test_unverified_organization_cannot_request_candidate_access(
    client,
    test_db,
    authenticated_client,
):
    _, organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="unverified-recruiter@example.com",
        role="recruiter",
        is_verified=False,
    )

    candidate_user, _ = authenticated_client(
        email="unverified-candidate@example.com",
    )
    candidate = create_candidate(test_db, user_id=candidate_user.id)

    response = client.post(
        "/api/v1/candidate-access/requests",
        params={"organization_id": organization.id},
        json={"candidate_id": candidate.id},
        headers=headers,
    )

    assert response.status_code == 403


def test_inactive_organization_cannot_request_candidate_access(
    client,
    test_db,
    authenticated_client,
):
    _, organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="inactive-recruiter@example.com",
        role="recruiter",
        is_active=False,
    )

    candidate_user, _ = authenticated_client(
        email="inactive-candidate@example.com",
    )
    candidate = create_candidate(test_db, user_id=candidate_user.id)

    response = client.post(
        "/api/v1/candidate-access/requests",
        params={"organization_id": organization.id},
        json={"candidate_id": candidate.id},
        headers=headers,
    )

    assert response.status_code == 403


def test_suspended_member_cannot_request_candidate_access(
    client,
    test_db,
    authenticated_client,
):
    _, organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="suspended-recruiter@example.com",
        role="recruiter",
        membership_status="suspended",
    )

    candidate_user, _ = authenticated_client(
        email="suspended-candidate@example.com",
    )
    candidate = create_candidate(test_db, user_id=candidate_user.id)

    response = client.post(
        "/api/v1/candidate-access/requests",
        params={"organization_id": organization.id},
        json={"candidate_id": candidate.id},
        headers=headers,
    )

    assert response.status_code == 403


def test_job_seeker_cannot_request_candidate_access(
    client,
    test_db,
    authenticated_client,
):
    _, organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="jobseeker-recruiter@example.com",
        role="job_seeker",
    )

    candidate_user, _ = authenticated_client(
        email="role-candidate@example.com",
    )
    candidate = create_candidate(test_db, user_id=candidate_user.id)

    response = client.post(
        "/api/v1/candidate-access/requests",
        params={"organization_id": organization.id},
        json={"candidate_id": candidate.id},
        headers=headers,
    )

    assert response.status_code == 403

def test_unauthenticated_user_cannot_request_candidate_access(
    client,
    test_db,
    authenticated_client,
):
    _, organization, _ = create_verified_company_member(
        authenticated_client,
        test_db,
        email="private-company@example.com",
        role="recruiter",
    )

    response = client.post(
        "/api/v1/candidate-access/requests",
        params={"organization_id": organization.id},
        json={"candidate_id": 999},
    )

    assert response.status_code == 401

def test_missing_candidate_returns_404(
    client,
    test_db,
    authenticated_client,
):
    _, organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="missing-candidate-recruiter@example.com",
        role="recruiter",
    )

    response = client.post(
        "/api/v1/candidate-access/requests",
        params={"organization_id": organization.id},
        json={"candidate_id": 99999},
        headers=headers,
    )

    assert response.status_code == 404


def test_candidate_without_account_owner_cannot_receive_access_request(
    client,
    test_db,
    authenticated_client,
):
    _, organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="ownerless-recruiter@example.com",
        role="recruiter",
    )

    candidate = create_candidate(test_db)

    response = client.post(
        "/api/v1/candidate-access/requests",
        params={"organization_id": organization.id},
        json={"candidate_id": candidate.id},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "This candidate does not have an account owner "
        "who can approve access."
    )

    access_record = test_db.scalar(
        select(CandidateOrganizationAccess).where(
            CandidateOrganizationAccess.candidate_id == candidate.id,
            CandidateOrganizationAccess.organization_id == organization.id,
        )
    )

    audit_event = test_db.scalar(
        select(CandidateAccessAuditEvent).where(
            CandidateAccessAuditEvent.candidate_id_snapshot == candidate.id,
            CandidateAccessAuditEvent.organization_id_snapshot == organization.id,
        )
    )

    assert access_record is None
    assert audit_event is None



def test_rejected_access_request_can_be_submitted_again(
    client,
    test_db,
    authenticated_client,
):
    recruiter, organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="rerequest-recruiter@example.com",
        role="recruiter",
    )

    candidate_user, _ = authenticated_client(
        email="rerequest-candidate@example.com",
    )

    candidate = create_candidate(
        test_db,
        user_id=candidate_user.id,
    )

    existing_access = CandidateOrganizationAccess(
        candidate_id=candidate.id,
        organization_id=organization.id,
        requested_by_user_id=recruiter.id,
        access_status="rejected",
    )

    test_db.add(existing_access)
    test_db.commit()

    response = client.post(
        "/api/v1/candidate-access/requests",
        params={"organization_id": organization.id},
        json={"candidate_id": candidate.id},
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["access_status"] == "pending"
    assert data["candidate_id"] == candidate.id
    assert data["organization_id"] == organization.id
    assert data["requested_by_user_id"] == recruiter.id

    access_records = test_db.scalars(
        select(CandidateOrganizationAccess).where(
            CandidateOrganizationAccess.candidate_id == candidate.id,
            CandidateOrganizationAccess.organization_id == organization.id,
        )
    ).all()

    assert len(access_records) == 1

    updated_access = access_records[0]

    assert updated_access.access_status == "pending"
    assert updated_access.requested_by_user_id == recruiter.id
    assert updated_access.granted_at is None
    assert updated_access.revoked_at is None

    audit_events = test_db.scalars(
        select(CandidateAccessAuditEvent).where(
            CandidateAccessAuditEvent.candidate_id_snapshot == candidate.id,
            CandidateAccessAuditEvent.organization_id_snapshot == organization.id,
        ).order_by(CandidateAccessAuditEvent.id)
    ).all()

    assert len(audit_events) == 1

    assert audit_events[0].event_type == "requested"
    assert audit_events[0].previous_status == "rejected"
    assert audit_events[0].new_status == "pending"
    assert audit_events[0].actor_user_id_snapshot == recruiter.id


def test_revoked_access_request_can_be_submitted_again(
    client,
    test_db,
    authenticated_client,
):
    recruiter, organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="revoked-recruiter@example.com",
        role="recruiter",
    )

    candidate_user, _ = authenticated_client(
        email="revoked-candidate@example.com",
    )

    candidate = create_candidate(
        test_db,
        user_id=candidate_user.id,
    )

    existing_access = CandidateOrganizationAccess(
        candidate_id=candidate.id,
        organization_id=organization.id,
        requested_by_user_id=recruiter.id,
        access_status="revoked",
    )

    test_db.add(existing_access)
    test_db.commit()

    response = client.post(
        "/api/v1/candidate-access/requests",
        params={"organization_id": organization.id},
        json={"candidate_id": candidate.id},
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["access_status"] == "pending"
    assert data["candidate_id"] == candidate.id
    assert data["organization_id"] == organization.id

    access_records = test_db.scalars(
        select(CandidateOrganizationAccess).where(
            CandidateOrganizationAccess.candidate_id == candidate.id,
            CandidateOrganizationAccess.organization_id == organization.id,
        )
    ).all()

    assert len(access_records) == 1

    updated_access = access_records[0]

    assert updated_access.access_status == "pending"
    assert updated_access.requested_by_user_id == recruiter.id
    assert updated_access.granted_at is None
    assert updated_access.revoked_at is None

    audit_event = test_db.scalar(
        select(CandidateAccessAuditEvent).where(
            CandidateAccessAuditEvent.candidate_id_snapshot == candidate.id,
            CandidateAccessAuditEvent.organization_id_snapshot == organization.id,
        )
    )

    assert audit_event is not None
    assert audit_event.previous_status == "revoked"
    assert audit_event.new_status == "pending"


def create_pending_access_request(
    test_db,
    candidate,
    organization,
    recruiter_user,
):
    access_request = CandidateOrganizationAccess(
        candidate_id=candidate.id,
        organization_id=organization.id,
        requested_by_user_id=recruiter_user.id,
        access_status="pending",
    )

    test_db.add(access_request)
    test_db.flush()

    test_db.add(
        CandidateAccessAuditEvent(
            candidate_id=candidate.id,
            organization_id=organization.id,
            actor_user_id=recruiter_user.id,
            candidate_id_snapshot=candidate.id,
            organization_id_snapshot=organization.id,
            actor_user_id_snapshot=recruiter_user.id,
            event_type="requested",
            previous_status=None,
            new_status="pending",
        )
    )

    test_db.commit()
    test_db.refresh(access_request)

    return access_request


def test_candidate_can_view_own_access_requests(
    client,
    test_db,
    authenticated_client,
):
    recruiter, organization, recruiter_headers = (
        create_verified_company_member(
            authenticated_client,
            test_db,
            email="view-requests-recruiter@example.com",
        )
    )

    candidate_user, candidate_headers = authenticated_client(
        email="view-requests-candidate@example.com",
    )

    other_candidate_user, _ = authenticated_client(
        email="other-view-candidate@example.com",
    )

    candidate = create_candidate(
        test_db,
        candidate_user.id,
        email="view-candidate@example.com",
    )

    other_candidate = create_candidate(
        test_db,
        other_candidate_user.id,
        email="other-view-candidate@example.com",
    )

    create_pending_access_request(
        test_db,
        candidate,
        organization,
        recruiter,
    )

    create_pending_access_request(
        test_db,
        other_candidate,
        organization,
        recruiter,
    )

    response = client.get(
        "/api/v1/candidate-access/requests/mine",
        headers=candidate_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["candidate_id"] == candidate.id
    assert data[0]["access_status"] == "pending"


def test_candidate_can_grant_access_request(
    client,
    test_db,
    authenticated_client,
):
    recruiter, organization, _ = create_verified_company_member(
        authenticated_client,
        test_db,
        email="grant-recruiter@example.com",
    )

    candidate_user, candidate_headers = authenticated_client(
        email="grant-candidate@example.com",
    )

    candidate = create_candidate(test_db, candidate_user.id)

    access_request = create_pending_access_request(
        test_db,
        candidate,
        organization,
        recruiter,
    )

    response = client.patch(
        f"/api/v1/candidate-access/requests/{access_request.id}/decision",
        json={"decision": "granted"},
        headers=candidate_headers,
    )

    assert response.status_code == 200
    assert response.json()["access_status"] == "granted"
    assert response.json()["granted_at"] is not None

    test_db.refresh(access_request)

    assert access_request.access_status == "granted"
    assert access_request.granted_at is not None

    audit_events = test_db.scalars(
        select(CandidateAccessAuditEvent).where(
            CandidateAccessAuditEvent.candidate_id_snapshot == candidate.id,
            CandidateAccessAuditEvent.event_type == "granted",
        )
    ).all()

    assert len(audit_events) == 1
    assert audit_events[0].previous_status == "pending"
    assert audit_events[0].new_status == "granted"
    assert audit_events[0].actor_user_id_snapshot == candidate_user.id


def test_candidate_can_reject_access_request(
    client,
    test_db,
    authenticated_client,
):
    recruiter, organization, _ = create_verified_company_member(
        authenticated_client,
        test_db,
        email="reject-recruiter@example.com",
    )

    candidate_user, candidate_headers = authenticated_client(
        email="reject-candidate@example.com",
    )

    candidate = create_candidate(test_db, candidate_user.id)

    access_request = create_pending_access_request(
        test_db,
        candidate,
        organization,
        recruiter,
    )

    response = client.patch(
        f"/api/v1/candidate-access/requests/{access_request.id}/decision",
        json={"decision": "rejected"},
        headers=candidate_headers,
    )

    assert response.status_code == 200
    assert response.json()["access_status"] == "rejected"

    test_db.refresh(access_request)

    assert access_request.access_status == "rejected"
    assert access_request.granted_at is None

    audit_events = test_db.scalars(
        select(CandidateAccessAuditEvent).where(
            CandidateAccessAuditEvent.candidate_id_snapshot == candidate.id,
            CandidateAccessAuditEvent.event_type == "rejected",
        )
    ).all()

    assert len(audit_events) == 1
    assert audit_events[0].previous_status == "pending"
    assert audit_events[0].new_status == "rejected"
    assert audit_events[0].actor_user_id_snapshot == candidate_user.id


def test_candidate_can_revoke_granted_access(
    client,
    test_db,
    authenticated_client,
):
    recruiter, organization, _ = create_verified_company_member(
        authenticated_client,
        test_db,
        email="revoke-recruiter@example.com",
    )

    candidate_user, candidate_headers = authenticated_client(
        email="revoke-candidate@example.com",
    )

    candidate = create_candidate(test_db, candidate_user.id)

    access_request = create_pending_access_request(
        test_db,
        candidate,
        organization,
        recruiter,
    )

    grant_response = client.patch(
        f"/api/v1/candidate-access/requests/{access_request.id}/decision",
        json={"decision": "granted"},
        headers=candidate_headers,
    )

    assert grant_response.status_code == 200

    revoke_response = client.patch(
        f"/api/v1/candidate-access/requests/{access_request.id}/decision",
        json={"decision": "revoked"},
        headers=candidate_headers,
    )

    assert revoke_response.status_code == 200
    assert revoke_response.json()["access_status"] == "revoked"
    assert revoke_response.json()["revoked_at"] is not None

    test_db.refresh(access_request)

    assert access_request.access_status == "revoked"
    assert access_request.revoked_at is not None

    audit_events = test_db.scalars(
        select(CandidateAccessAuditEvent).where(
            CandidateAccessAuditEvent.candidate_id_snapshot == candidate.id,
        )
    ).all()

    event_types = [event.event_type for event in audit_events]

    assert "requested" in event_types
    assert "granted" in event_types
    assert "revoked" in event_types


def test_another_candidate_cannot_decide_access_request(
    client,
    test_db,
    authenticated_client,
):
    recruiter, organization, _ = create_verified_company_member(
        authenticated_client,
        test_db,
        email="ownership-recruiter@example.com",
    )

    candidate_user, _ = authenticated_client(
        email="request-owner@example.com",
    )

    other_user, other_headers = authenticated_client(
        email="unauthorized-candidate@example.com",
    )

    candidate = create_candidate(test_db, candidate_user.id)

    access_request = create_pending_access_request(
        test_db,
        candidate,
        organization,
        recruiter,
    )

    response = client.patch(
        f"/api/v1/candidate-access/requests/{access_request.id}/decision",
        json={"decision": "granted"},
        headers=other_headers,
    )

    assert response.status_code == 404

    test_db.refresh(access_request)

    assert access_request.access_status == "pending"

    audit_events = test_db.scalars(
        select(CandidateAccessAuditEvent).where(
            CandidateAccessAuditEvent.candidate_id_snapshot == candidate.id,
        )
    ).all()

    assert len(audit_events) == 1
    assert audit_events[0].event_type == "requested"


def test_recruiter_can_view_candidate_after_access_is_granted(
    client,
    test_db,
    authenticated_client,
):
    _, organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="authorized-recruiter@example.com",
        role="recruiter",
    )

    candidate_user, _ = authenticated_client(
        email="authorized-candidate@example.com",
    )

    candidate = create_candidate(
        test_db,
        user_id=candidate_user.id,
    )

    access = CandidateOrganizationAccess(
        candidate_id=candidate.id,
        organization_id=organization.id,
        requested_by_user_id=1,
        access_status="granted",
    )

    test_db.add(access)
    test_db.commit()

    response = client.get(
        f"/api/v1/candidate-access/candidates/{candidate.id}",
        params={"organization_id": organization.id},
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == candidate.id
    assert data["full_name"] == candidate.full_name
    assert data["email"] == candidate.email

    # Internal information must never be exposed.
    assert "user_id" not in data
    assert "file_path" not in data
    assert "stored_filename" not in data
    assert "extracted_text" not in data
    assert "extracted_data" not in data


def test_recruiter_cannot_view_candidate_with_pending_access(
    client,
    test_db,
    authenticated_client,
):
    _, organization, headers = create_verified_company_member(
        authenticated_client,
        test_db,
        email="pending-recruiter@example.com",
        role="recruiter",
    )

    candidate_user, _ = authenticated_client(
        email="pending-candidate@example.com",
    )

    candidate = create_candidate(
        test_db,
        user_id=candidate_user.id,
    )

    access = CandidateOrganizationAccess(
        candidate_id=candidate.id,
        organization_id=organization.id,
        requested_by_user_id=1,
        access_status="pending",
    )

    test_db.add(access)
    test_db.commit()

    response = client.get(
        f"/api/v1/candidate-access/candidates/{candidate.id}",
        params={"organization_id": organization.id},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Candidate not found or access not granted."
    )


def test_another_organization_cannot_view_candidate(
    client,
    test_db,
    authenticated_client,
):
    recruiter, organization_a, _ = create_verified_company_member(
        authenticated_client,
        test_db,
        email="company-a-recruiter@example.com",
    )

    _, organization_b, headers_b = create_verified_company_member(
        authenticated_client,
        test_db,
        email="company-b-recruiter@example.com",
    )

    candidate_user, _ = authenticated_client(
        email="cross-company-candidate@example.com",
    )

    candidate = create_candidate(
        test_db,
        user_id=candidate_user.id,
    )

    access = CandidateOrganizationAccess(
        candidate_id=candidate.id,
        organization_id=organization_a.id,
        requested_by_user_id=recruiter.id,
        access_status="granted",
    )

    test_db.add(access)
    test_db.commit()

    response = client.get(
        f"/api/v1/candidate-access/candidates/{candidate.id}",
        params={"organization_id": organization_b.id},
        headers=headers_b,
    )

    assert response.status_code == 404


def test_recruiter_cannot_view_candidate_after_consent_is_revoked(
    client,
    test_db,
    authenticated_client,
):
    recruiter, organization, recruiter_headers = (
        create_verified_company_member(
            authenticated_client,
            test_db,
            email="revoked-recruiter@example.com",
        )
    )

    candidate_user, candidate_headers = authenticated_client(
        email="revoked-candidate@example.com",
    )

    candidate = create_candidate(
        test_db,
        user_id=candidate_user.id,
    )

    access = CandidateOrganizationAccess(
        candidate_id=candidate.id,
        organization_id=organization.id,
        requested_by_user_id=recruiter.id,
        access_status="granted",
    )

    test_db.add(access)
    test_db.commit()

    # Candidate revokes the previously granted access.
    revoke_response = client.patch(
        f"/api/v1/candidate-access/requests/{access.id}/decision",
        json={"decision": "revoked"},
        headers=candidate_headers,
    )

    assert revoke_response.status_code == 200
    assert revoke_response.json()["access_status"] == "revoked"

    # Recruiter must immediately lose access.
    profile_response = client.get(
        f"/api/v1/candidate-access/candidates/{candidate.id}",
        params={"organization_id": organization.id},
        headers=recruiter_headers,
    )

    assert profile_response.status_code == 404


def test_recruiter_can_view_only_approved_cv_information(
    client,
    test_db,
    authenticated_client,
):
    recruiter, organization, recruiter_headers = (
        create_verified_company_member(
            authenticated_client,
            test_db,
            email="cv-recruiter@example.com",
        )
    )

    candidate_user, _ = authenticated_client(
        email="cv-candidate@example.com",
    )

    candidate = create_candidate(
        test_db,
        user_id=candidate_user.id,
    )

    access = CandidateOrganizationAccess(
        candidate_id=candidate.id,
        organization_id=organization.id,
        requested_by_user_id=recruiter.id,
        access_status="granted",
    )
    test_db.add(access)

    approved_cv = CVDocument(
        candidate_id=candidate.id,
        original_filename="approved_cv.pdf",
        stored_filename="internal-approved-123.pdf",
        file_path="private/uploads/internal-approved-123.pdf",
        file_type="pdf",
        file_size=1024,
        extracted_text="Private extracted text",
        extracted_data={"full_name": "AI extracted name"},
        approved_data={"full_name": "Candidate Approved Name"},
        processing_status="processed",
        review_status="approved",
        reviewed_at=datetime.now(timezone.utc),
    )

    pending_cv = CVDocument(
        candidate_id=candidate.id,
        original_filename="pending_cv.pdf",
        stored_filename="internal-pending-456.pdf",
        file_path="private/uploads/internal-pending-456.pdf",
        file_type="pdf",
        file_size=2048,
        extracted_text="Unreviewed text",
        extracted_data={"full_name": "Unreviewed name"},
        approved_data=None,
        processing_status="processed",
        review_status="pending_review",
    )

    test_db.add_all([approved_cv, pending_cv])
    test_db.commit()

    response = client.get(
        f"/api/v1/candidate-access/candidates/{candidate.id}/cvs",
        params={"organization_id": organization.id},
        headers=recruiter_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == approved_cv.id
    assert data[0]["approved_data"]["full_name"] == (
        "Candidate Approved Name"
    )
    assert data[0]["review_status"] == "approved"

    for private_field in (
        "file_path",
        "stored_filename",
        "extracted_text",
        "extracted_data",
    ):
        assert private_field not in data[0]


def test_recruiter_cannot_view_cvs_without_granted_consent(
    client,
    test_db,
    authenticated_client,
):
    recruiter, organization, recruiter_headers = (
        create_verified_company_member(
            authenticated_client,
            test_db,
            email="pending-cv-recruiter@example.com",
        )
    )

    candidate_user, _ = authenticated_client(
        email="pending-cv-candidate@example.com",
    )

    candidate = create_candidate(
        test_db,
        user_id=candidate_user.id,
    )

    access = CandidateOrganizationAccess(
        candidate_id=candidate.id,
        organization_id=organization.id,
        requested_by_user_id=recruiter.id,
        access_status="pending",
    )

    test_db.add(access)
    test_db.commit()

    response = client.get(
        f"/api/v1/candidate-access/candidates/{candidate.id}/cvs",
        params={"organization_id": organization.id},
        headers=recruiter_headers,
    )

    assert response.status_code == 404


def test_recruiter_receives_empty_list_when_candidate_has_no_approved_cvs(
    client,
    test_db,
    authenticated_client,
):
    recruiter, organization, recruiter_headers = (
        create_verified_company_member(
            authenticated_client,
            test_db,
            email="empty-cv-recruiter@example.com",
        )
    )

    candidate_user, _ = authenticated_client(
        email="empty-cv-candidate@example.com",
    )

    candidate = create_candidate(
        test_db,
        user_id=candidate_user.id,
    )

    access = CandidateOrganizationAccess(
        candidate_id=candidate.id,
        organization_id=organization.id,
        requested_by_user_id=recruiter.id,
        access_status="granted",
    )

    test_db.add(access)
    test_db.commit()

    response = client.get(
        f"/api/v1/candidate-access/candidates/{candidate.id}/cvs",
        params={"organization_id": organization.id},
        headers=recruiter_headers,
    )

    assert response.status_code == 200
    assert response.json() == []
