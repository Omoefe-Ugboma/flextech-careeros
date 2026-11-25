
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Candidate,
    CandidateOrganizationAccess,
    CandidateAccessAuditEvent,
    CVDocument,
)


DUPLICATE_REQUEST_MESSAGE = (
    "An active or pending access request already exists."
)


def _lock_candidate_organization_pair(
    db: Session,
    candidate_id: int,
    organization_id: int,
) -> None:
    """
    Serialize access requests for the same candidate and organization.

    PostgreSQL transaction-level advisory locks also work when the
    access record does not exist yet. SQLite skips this lock.
    """

    if db.get_bind().dialect.name != "postgresql":
        return

    # Both IDs are positive PostgreSQL INTEGER values.
    # Combining them produces a deterministic signed BIGINT lock key.
    lock_key = (candidate_id << 32) | organization_id

    db.execute(
        select(func.pg_advisory_xact_lock(lock_key))
    )


def _is_access_pair_unique_violation(
    exc: IntegrityError,
) -> bool:
    """
    Identify violations of the candidate/organization unique constraint.
    Do not misclassify unrelated database integrity errors.
    """

    original_error = exc.orig

    diagnostic = getattr(original_error, "diag", None)
    constraint_name = getattr(
        diagnostic,
        "constraint_name",
        None,
    )

    if constraint_name == "uq_candidate_organization_access":
        return True

    # SQLite does not expose PostgreSQL-style constraint diagnostics.
    error_message = str(original_error)

    return (
        "UNIQUE constraint failed: "
        "candidate_organization_access.candidate_id, "
        "candidate_organization_access.organization_id"
    ) in error_message


def create_candidate_access_request(
    db: Session,
    *,
    candidate_id: int,
    organization_id: int,
    requested_by_user_id: int,
) -> CandidateOrganizationAccess:

    try:
        _lock_candidate_organization_pair(
            db,
            candidate_id,
            organization_id,
        )

        candidate = db.scalar(
            select(Candidate).where(
                Candidate.id == candidate_id,
            )
        )

        if candidate is None:
            raise ValueError("Candidate not found.")

        if candidate.user_id is None:
            raise ValueError(
                "This candidate does not have an account owner "
                "who can approve access."
            )

        existing_access = db.scalar(
            select(CandidateOrganizationAccess)
            .where(
                CandidateOrganizationAccess.candidate_id == candidate_id,
                CandidateOrganizationAccess.organization_id == organization_id,
            )
            .with_for_update()
        )

        if existing_access is not None:
            if existing_access.access_status in {"pending", "granted"}:
                raise ValueError(DUPLICATE_REQUEST_MESSAGE)

            previous_status = existing_access.access_status

            existing_access.requested_by_user_id = requested_by_user_id
            existing_access.access_status = "pending"
            existing_access.requested_at = datetime.now(timezone.utc)
            existing_access.granted_at = None
            existing_access.revoked_at = None

        else:
            previous_status = None

            existing_access = CandidateOrganizationAccess(
                candidate_id=candidate_id,
                organization_id=organization_id,
                requested_by_user_id=requested_by_user_id,
                access_status="pending",
            )

            db.add(existing_access)

        # Persist the access record before creating its audit event.
        db.flush()

        audit_event = CandidateAccessAuditEvent(
            candidate_id=candidate_id,
            organization_id=organization_id,
            actor_user_id=requested_by_user_id,
            candidate_id_snapshot=candidate_id,
            organization_id_snapshot=organization_id,
            actor_user_id_snapshot=requested_by_user_id,
            event_type="requested",
            previous_status=previous_status,
            new_status="pending",
        )

        db.add(audit_event)

        # Both changes commit together.
        db.commit()

        db.refresh(existing_access)

        return existing_access

    except IntegrityError as exc:
        db.rollback()

        if _is_access_pair_unique_violation(exc):
            raise ValueError(DUPLICATE_REQUEST_MESSAGE) from exc

        # Preserve the original error for unexpected integrity failures.
        raise

    except Exception:
        db.rollback()
        raise


def list_candidate_access_requests(
    db: Session,
    *,
    candidate_owner_user_id: int,
) -> list[CandidateOrganizationAccess]:
    """
    Return access requests belonging only to the authenticated
    candidate owner.
    """

    statement = (
        select(CandidateOrganizationAccess)
        .join(
            Candidate,
            Candidate.id == CandidateOrganizationAccess.candidate_id,
        )
        .where(
            Candidate.user_id == candidate_owner_user_id,
        )
        .order_by(
            CandidateOrganizationAccess.requested_at.desc(),
        )
    )

    return list(db.scalars(statement).all())


def update_candidate_access_decision(
    db: Session,
    *,
    access_request_id: int,
    candidate_owner_user_id: int,
    decision: str,
) -> CandidateOrganizationAccess:
    """
    Allow the candidate who owns the profile to grant, reject,
    or revoke an organization's access.

    Every decision and its audit event are committed together.
    """

    allowed_decisions = {"granted", "rejected", "revoked"}

    if decision not in allowed_decisions:
        raise ValueError("Invalid access decision.")

    try:
        # Lock the request and verify candidate ownership together.
        access_request = db.scalar(
            select(CandidateOrganizationAccess)
            .join(
                Candidate,
                Candidate.id == CandidateOrganizationAccess.candidate_id,
            )
            .where(
                CandidateOrganizationAccess.id == access_request_id,
                Candidate.user_id == candidate_owner_user_id,
            )
            .with_for_update()
        )

        if access_request is None:
            raise ValueError("Access request not found.")

        previous_status = access_request.access_status

        # Enforce valid state transitions.
        if decision in {"granted", "rejected"}:
            if previous_status != "pending":
                raise ValueError(
                    "Only pending requests can be granted or rejected."
                )

        elif decision == "revoked":
            if previous_status != "granted":
                raise ValueError(
                    "Only granted access can be revoked."
                )

        now = datetime.now(timezone.utc)

        access_request.access_status = decision

        if decision == "granted":
            access_request.granted_at = now
            access_request.revoked_at = None

        elif decision == "rejected":
            access_request.granted_at = None
            access_request.revoked_at = None

        elif decision == "revoked":
            access_request.revoked_at = now

        db.flush()

        audit_event = CandidateAccessAuditEvent(
            candidate_id=access_request.candidate_id,
            organization_id=access_request.organization_id,
            actor_user_id=candidate_owner_user_id,
            candidate_id_snapshot=access_request.candidate_id,
            organization_id_snapshot=access_request.organization_id,
            actor_user_id_snapshot=candidate_owner_user_id,
            event_type=decision,
            previous_status=previous_status,
            new_status=decision,
        )

        db.add(audit_event)

        db.commit()
        db.refresh(access_request)

        return access_request

    except Exception:
        db.rollback()
        raise


def get_candidate_for_organization(
    db: Session,
    *,
    candidate_id: int,
    organization_id: int,
) -> Candidate:
    """
    Return a candidate only when that candidate has
    granted access to the requesting organization.
    """

    statement = (
        select(Candidate)
        .join(
            CandidateOrganizationAccess,
            CandidateOrganizationAccess.candidate_id == Candidate.id,
        )
        .where(
            Candidate.id == candidate_id,
            CandidateOrganizationAccess.organization_id == organization_id,
            CandidateOrganizationAccess.access_status == "granted",
        )
    )

    candidate = db.scalar(statement)

    if candidate is None:
        raise ValueError("Candidate not found or access not granted.")

    return candidate


def get_approved_cvs_for_organization(
    db: Session,
    *,
    candidate_id: int,
    organization_id: int,
) -> list[CVDocument]:
    """
    Return only candidate-approved CV documents when the
    candidate has granted access to the specified organization.
    """

    statement = (
        select(CandidateOrganizationAccess.id, CVDocument)
        .outerjoin(
            CVDocument,
            (
                CVDocument.candidate_id
                == CandidateOrganizationAccess.candidate_id
            )
            & (CVDocument.processing_status == "processed")
            & (CVDocument.review_status == "approved")
            & (CVDocument.approved_data.is_not(None))
            & (CVDocument.reviewed_at.is_not(None)),
        )
        .where(
            CandidateOrganizationAccess.candidate_id == candidate_id,
            CandidateOrganizationAccess.organization_id == organization_id,
            CandidateOrganizationAccess.access_status == "granted",
        )
        .order_by(CVDocument.created_at.desc())
    )

    rows = db.execute(statement).all()

    if not rows:
        raise ValueError("Candidate not found or access not granted.")

    return [
        cv_document
        for _, cv_document in rows
        if cv_document is not None
    ]
