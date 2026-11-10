from pydantic import BaseModel, Field


class EducationEntry(BaseModel):
    institution: str | None = None
    qualification: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class WorkExperienceEntry(BaseModel):
    job_title: str | None = None
    company: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    responsibilities: list[str] = Field(default_factory=list)


class ProjectEntry(BaseModel):
    name: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)


class CertificationEntry(BaseModel):
    name: str | None = None
    issuing_organization: str | None = None
    date_obtained: str | None = None


class CVExtraction(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None

    professional_headline: str | None = None
    professional_summary: str | None = None

    skills: list[str] = Field(default_factory=list)

    education: list[EducationEntry] = Field(default_factory=list)

    work_experience: list[WorkExperienceEntry] = Field(
        default_factory=list
    )

    projects: list[ProjectEntry] = Field(default_factory=list)

    certifications: list[CertificationEntry] = Field(
        default_factory=list
    )