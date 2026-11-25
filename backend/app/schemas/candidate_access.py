
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CandidateAccessRequestCreate(BaseModel):
    candidate_id: int = Field(gt=0)


class CandidateAccessRequestRead(BaseModel):
    id: int
    candidate_id: int
    organization_id: int
    requested_by_user_id: int
    access_status: Literal[
        "pending",
        "granted",
        "rejected",
        "revoked",
    ]
    requested_at: datetime
    granted_at: datetime | None
    revoked_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

class CandidateAccessDecision(BaseModel):
    decision: Literal[
        "granted",
        "rejected",
        "revoked",
    ]


class CandidateRecruiterRead(BaseModel):
    """
    Candidate information visible to an organization
    after the candidate grants access.
    """

    id: int
    full_name: str
    email: str
    phone: str | None
    location: str | None
    professional_headline: str | None
    professional_summary: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
