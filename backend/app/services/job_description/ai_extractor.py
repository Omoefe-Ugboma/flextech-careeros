
from openai import OpenAI

from app.core.database import settings
from app.schemas.job_description import JobDescriptionExtraction


client = OpenAI(api_key=settings.OPENAI_API_KEY)


def extract_job_requirements(
    description: str,
) -> JobDescriptionExtraction:

    if not description.strip():
        raise ValueError("Job description cannot be empty.")

    response = client.responses.parse(
        model=settings.OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "You are an expert technical recruitment analyst. "
                    "Extract requirements strictly from the supplied "
                    "job description. Never invent qualifications, "
                    "skills, responsibilities, or experience requirements. "
                    "Separate required skills from preferred skills. "
                    "Preserve experience requirements in their original wording, "
                    "including ranges such as 3-5 years or phrases such as "
                    "'at least 3 years'. "
                    "If experience requirements are not explicitly stated, "
                    "return null for experience_requirement. "
                    "If information is missing, use null for optional fields "
                    "and empty lists for collections."
                ),
            },
            {
                "role": "user",
                "content": description,
            },
        ],
        text_format=JobDescriptionExtraction,
    )

    result = response.output_parsed

    if result is None:
        raise ValueError(
            "AI could not extract job requirements."
        )

    return result
