
from app.services.matching.skill_matcher import (
    build_complete_skill_match_result,
)

from app.services.matching.qualification_matcher import (
    assess_qualification,
)

from app.services.matching.qualification_parser import (
    extract_academic_level,
    extract_academic_field,
)

from app.services.matching.experience_matcher import (
    assess_experience,
)


def build_qualification_match_result(
    approved_cv: dict,
    qualifications: list[str],
) -> dict:

    if not qualifications:
        return {
            "status": "not_required",
            "reason": "No academic qualification requirement specified",
            "evidence": [],
        }

    results = []

    for requirement in qualifications:
        required_level = extract_academic_level(requirement)

        if required_level is None:
            required_field = extract_academic_field(requirement)

            if "equivalent experience" in requirement.lower():
                results.append({
                    "requirement": requirement,
                    "academic_requirement": {
                        "status": "unknown",
                        "required_level": None,
                        "required_field": required_field,
                    },
                    "equivalent_experience": {
                        "status": "not_assessed",
                    },
                })
            else:
                results.append({
                    "requirement": requirement,
                    "status": "unknown",
                    "reason": "Academic qualification level could not be identified",
                    "evidence": [],
                })

            continue

        required_field = extract_academic_field(requirement)

        assessment = assess_qualification(
            education=approved_cv.get("education", []),
            required_level=required_level,
            required_field=required_field,
        )

        results.append({
            "requirement": requirement,
            "required_level": required_level,
            "required_field": required_field,
            **assessment,
        })

    statuses = []

    for result in results:
        if "academic_requirement" in result:
            statuses.append(
                result["academic_requirement"]["status"]
            )
        else:
            statuses.append(result["status"])

    if all(status == "met" for status in statuses):
        overall_status = "met"
    elif "not_met" in statuses:
        overall_status = "not_met"
    else:
        overall_status = "unknown"

    return {
        "status": overall_status,
        "requirements": results,
    }

def build_complete_match_result(
    approved_cv: dict,
    job_data: dict,
) -> dict:

    # 1. Assess required and preferred skills.
    skill_results = build_complete_skill_match_result(
        approved_cv=approved_cv,
        required_skills=job_data.get("required_skills", []),
        preferred_skills=job_data.get("preferred_skills", []),
    )

    # 2. Assess academic qualifications.
    qualification_results = build_qualification_match_result(
        approved_cv=approved_cv,
        qualifications=job_data.get("qualifications", []),
    )

    # 3. Assess professional experience.
    experience_results = assess_experience(
        work_experience=approved_cv.get("work_experience", []),
        required_experience=job_data.get("experience_requirement"),
    )

    return {
        "skills": skill_results,
        "qualifications": qualification_results,
        "experience": experience_results,
    }