
from openai import OpenAI

from app.core.database import settings
from app.schemas.cv_extraction import CVExtraction


client = OpenAI(api_key=settings.OPENAI_API_KEY)


def extract_candidate_information(cv_text: str) -> CVExtraction:
    if not cv_text.strip():
        raise ValueError("CV text cannot be empty.")

    response = client.responses.parse(
        model=settings.OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a professional CV information extraction "
                    "assistant. Extract information strictly from the "
                    "provided CV. Never invent or assume information. "
                    "Use null for missing individual fields and empty "
                    "lists for missing collections. Preserve the "
                    "candidate's original meaning."
                ),
            },
            {
                "role": "user",
                "content": cv_text,
            },
        ],
        text_format=CVExtraction,
    )

    result = response.output_parsed

    if result is None:
        raise ValueError("AI could not extract structured CV information.")

    return result
