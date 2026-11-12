
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobDescriptionCreate(BaseModel):
    job_title: str = Field(min_length=2, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    original_description: str = Field(min_length=50)


class JobDescriptionExtraction(BaseModel):
    responsibilities: list[str] = Field(default_factory=list)

    required_skills: list[str] = Field(default_factory=list)

    preferred_skills: list[str] = Field(default_factory=list)

    qualifications: list[str] = Field(default_factory=list)

    experience_requirement: str | None = None

    employment_type: str | None = None


class JobDescriptionRead(BaseModel):
    id: int
    job_title: str
    company_name: str | None
    location: str | None
    original_description: str
    extracted_data: dict | None
    processing_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
