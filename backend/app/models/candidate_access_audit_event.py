
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CandidateAccessAuditEvent(Base):
    __tablename__ = "candidate_access_audit_events"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    # Nullable foreign keys preserve audit history if an entity is deleted.
    candidate_id: Mapped[int | None] = mapped_column(
        ForeignKey("candidates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Original IDs retained for historical reference.
    candidate_id_snapshot: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    organization_id_snapshot: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    actor_user_id_snapshot: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    previous_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    new_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
