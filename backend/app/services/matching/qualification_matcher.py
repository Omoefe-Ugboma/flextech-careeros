
QUALIFICATION_ALIASES = {
    "bsc": "bachelor",
    "b.sc": "bachelor",
    "bachelor of science": "bachelor",
    "ba": "bachelor",
    "b.a": "bachelor",
    "bachelor of arts": "bachelor",
    "bachelor's degree": "bachelor",
    "bachelors degree": "bachelor",
    "bachelor degree": "bachelor",

    "msc": "master",
    "m.sc": "master",
    "master of science": "master",
    "ma": "master",
    "m.a": "master",
    "master of arts": "master",
    "master's degree": "master",
    "masters degree": "master",
    
    "phd": "doctorate",
    "ph.d": "doctorate",
    "ph.d.": "doctorate",
    "doctor of philosophy": "doctorate",
    "doctoral degree": "doctorate",
    "doctorate": "doctorate",
    "bachelor": "bachelor",
    "master": "master",

}

FIELD_ALIASES = {
    "computer sciences": "computer science",
    "computing science": "computer science",
    "information technology": "information technology",
    "it": "information technology",
}


QUALIFICATION_LEVELS = {
    "certificate": 1,
    "diploma": 2,
    "bachelor": 3,
    "master": 4,
    "doctorate": 5,
}


def normalize_qualification(
    qualification: str,
) -> str:
    normalized = qualification.strip().lower()

    return QUALIFICATION_ALIASES.get(
        normalized,
        normalized,
    )



def get_qualification_level(
    qualification: str,
) -> int | None:

    normalized = normalize_qualification(
        qualification
    )

    return QUALIFICATION_LEVELS.get(normalized)


def compare_qualification_levels(
    candidate_qualification: str,
    required_qualification: str,
) -> str:

    candidate_level = get_qualification_level(
        candidate_qualification
    )

    required_level = get_qualification_level(
        required_qualification
    )

    if candidate_level is None or required_level is None:
        return "unknown"

    if candidate_level >= required_level:
        return "met"

    return "not_met"



def assess_qualification(
    education: list[dict],
    required_level: str,
    required_field: str | None = None,
) -> dict:

    normalized_required_field = (
        normalize_field(required_field)
        if required_field
        else None
    )

    if not education:
        return {
            "status": "unknown",
            "reason": "No education records found",
            "evidence": [],
        }

    matching_evidence = []
    has_not_met_evidence = False
    has_unknown_evidence = False

    for record in education:
        candidate_level = record.get("qualification")
        candidate_field = record.get("field_of_study")

        if not candidate_level:
            has_unknown_evidence = True
            continue

        level_status = compare_qualification_levels(
            candidate_level,
            required_level,
        )

        if level_status == "unknown":
            has_unknown_evidence = True
            continue

        if level_status == "not_met":
            has_not_met_evidence = True
            continue

        if normalized_required_field:
            if not candidate_field:
                has_unknown_evidence = True
                continue

            normalized_candidate_field = normalize_field(
                candidate_field
            )

            if normalized_candidate_field != normalized_required_field:
                has_not_met_evidence = True
                continue

        matching_evidence.append({
            "qualification": candidate_level,
            "field_of_study": candidate_field,
            "institution": record.get("institution"),
        })

    if matching_evidence:
        return {
            "status": "met",
            "reason": "Qualification level and field requirements satisfied",
            "evidence": matching_evidence,
        }

    if has_not_met_evidence:
        return {
            "status": "not_met",
            "reason": "Available education records do not satisfy the requirement",
            "evidence": [],
        }

    return {
        "status": "unknown",
        "reason": "Insufficient education information to assess the requirement",
        "evidence": [],
    }


def normalize_field(field: str) -> str:
    normalized = field.strip().lower()

    return FIELD_ALIASES.get(
        normalized,
        normalized,
    )