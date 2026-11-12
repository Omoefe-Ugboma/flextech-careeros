
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CandidateJobMatchCreate(BaseModel):
    candidate_id: int = Field(gt=0)
    cv_document_id: int = Field(gt=0)
    job_description_id: int = Field(gt=0)


class CandidateJobMatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    cv_document_id: int
    job_description_id: int
    match_score: float | None
    match_results: dict
    created_at: datetime
