from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CandidateCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    location: str | None = Field(default=None, max_length=150)
    professional_headline: str | None = Field(default=None, max_length=255)
    professional_summary: str | None = None


class CandidateUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    location: str | None = Field(default=None, max_length=150)
    professional_headline: str | None = Field(default=None, max_length=255)
    professional_summary: str | None = None


class CandidateRead(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str | None
    location: str | None
    professional_headline: str | None
    professional_summary: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)