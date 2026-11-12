

import re


ACADEMIC_QUALIFICATION_PATTERNS = {
    "doctorate": [
        r"\bph\.?d\.?\b",
        r"\bdoctorate\b",
        r"\bdoctoral degree\b",
        r"\bdoctor of philosophy\b",
    ],
    "master": [
        r"\bm\.?sc\.?\b",
        r"\bm\.?a\.?\b",
        r"\bmaster(?:'s)? degree\b",
        r"\bmaster of science\b",
        r"\bmaster of arts\b",
    ],
    "bachelor": [
        r"\bb\.?sc\.?\b",
        r"\bb\.?a\.?\b",
        r"\bbachelor(?:'s)? degree\b",
        r"\bbachelor of science\b",
        r"\bbachelor of arts\b",
    ],
    "diploma": [
        r"\bdiploma\b",
    ],
    "certificate": [
        r"\bcertificate\b",
    ],
}


def extract_academic_level(
    qualification_text: str,
) -> str | None:
    normalized = qualification_text.strip().lower()

    for level, patterns in ACADEMIC_QUALIFICATION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                return level

    return None



def extract_academic_field(
    qualification_text: str,
) -> str | None:
    normalized = qualification_text.strip().lower()

    patterns = [
        r"\bdegree\s+in\s+([a-z][a-z\s&/-]*?)(?=\s+(?:or|and|with|plus)\b|[,;.]|$)",
        r"\b(?:b\.?sc\.?|b\.?a\.?|m\.?sc\.?|m\.?a\.?|ph\.?d\.?)\s+in\s+([a-z][a-z\s&/-]*?)(?=\s+(?:or|and|with|plus)\b|[,;.]|$)",
        r"\bdiploma\s+in\s+([a-z][a-z\s&/-]*?)(?=\s+(?:or|and|with|plus)\b|[,;.]|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized)

        if match:
            return match.group(1).strip()

    return None
