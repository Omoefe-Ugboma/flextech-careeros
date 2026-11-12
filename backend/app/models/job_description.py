
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    job_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    company_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    original_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    extracted_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    processing_status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
