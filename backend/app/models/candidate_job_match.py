
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Float,
    Integer,
    func,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CandidateJobMatch(Base):
    __tablename__ = "candidate_job_matches"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    candidate_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    cv_document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cv_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    job_description_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    match_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    match_results: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
