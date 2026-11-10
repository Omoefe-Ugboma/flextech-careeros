
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CVDocumentRead(BaseModel):
    id: int
    candidate_id: int
    original_filename: str
    stored_filename: str
    file_type: str
    file_size: int

    processing_status: str

    # Original AI-extracted information.
    extracted_data: dict[str, Any] | None = None

    # Candidate-reviewed information.
    approved_data: dict[str, Any] | None = None

    # Human review tracking.
    review_status: str
    reviewed_at: datetime | None = None

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
