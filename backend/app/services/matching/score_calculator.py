from typing import Any
import math

MATCH_WEIGHTS = {
    "skills": 50.0,
    "qualifications": 20.0,
    "experience": 30.0,
}


def calculate_match_score(match_results: dict[str, Any]) -> dict[str, Any]:
    """
    Calculate an explainable weighted candidate-job match score.

    Unknown and not_required criteria are excluded from the score.
    Assessment completeness measures how much of the total weighting
    could be assessed.
    """

    criteria = {}

    total_weighted_score = 0.0
    assessed_weight = 0.0

    # 1. Assess required skills.
    skill_coverage = (
        match_results.get("skills", {})
        .get("required_skills", {})
        .get("required_skill_coverage")
    )

    if skill_coverage is None:
        criteria["skills"] = {
            "weight": MATCH_WEIGHTS["skills"],
            "assessment": None,
            "weighted_score": None,
            "status": "unknown",
        }
    else:
        if (
            isinstance(skill_coverage, bool)
            or not isinstance(skill_coverage, (int, float))
            or not math.isfinite(skill_coverage)
        ):
            raise ValueError("Skill coverage must be a finite numeric value.")

        if not 0 <= skill_coverage <= 100:
            raise ValueError("Skill coverage must be between 0 and 100.")


        weighted_score = (
            skill_coverage * MATCH_WEIGHTS["skills"] / 100
        )

        criteria["skills"] = {
            "weight": MATCH_WEIGHTS["skills"],
            "assessment": float(skill_coverage),
            "weighted_score": round(weighted_score, 2),
            "status": "assessed",
        }

        total_weighted_score += weighted_score
        assessed_weight += MATCH_WEIGHTS["skills"]

    # 2. Assess academic qualifications.
    qualification_status = (
        match_results.get("qualifications", {})
        .get("status", "unknown")
    )

    if qualification_status not in {
        "met",
        "not_met",
        "unknown",
        "not_required",
    }:
        raise ValueError("Invalid qualification assessment status.")

    if qualification_status in {"met", "not_met"}:
        assessment = 100.0 if qualification_status == "met" else 0.0

        weighted_score = (
            assessment * MATCH_WEIGHTS["qualifications"] / 100
        )

        criteria["qualifications"] = {
            "weight": MATCH_WEIGHTS["qualifications"],
            "assessment": assessment,
            "weighted_score": round(weighted_score, 2),
            "status": qualification_status,
        }

        total_weighted_score += weighted_score
        assessed_weight += MATCH_WEIGHTS["qualifications"]

    else:
        criteria["qualifications"] = {
            "weight": MATCH_WEIGHTS["qualifications"],
            "assessment": None,
            "weighted_score": None,
            "status": qualification_status,
        }

    # 3. Assess professional experience.
    experience_status = (
        match_results.get("experience", {})
        .get("status", "unknown")
    )

    if experience_status not in {
        "met",
        "not_met",
        "unknown",
        "not_required",
    }:
        raise ValueError("Invalid experience assessment status.")

    if experience_status in {"met", "not_met"}:
        assessment = 100.0 if experience_status == "met" else 0.0

        weighted_score = (
            assessment * MATCH_WEIGHTS["experience"] / 100
        )

        criteria["experience"] = {
            "weight": MATCH_WEIGHTS["experience"],
            "assessment": assessment,
            "weighted_score": round(weighted_score, 2),
            "status": experience_status,
        }

        total_weighted_score += weighted_score
        assessed_weight += MATCH_WEIGHTS["experience"]

    else:
        criteria["experience"] = {
            "weight": MATCH_WEIGHTS["experience"],
            "assessment": None,
            "weighted_score": None,
            "status": experience_status,
        }

    # 4. Calculate the final score and assessment completeness.
    if assessed_weight == 0:
        overall_score = None
    else:
        overall_score = round(
            (total_weighted_score / assessed_weight) * 100,
            2,
        )

    assessment_completeness = round(
        (assessed_weight / 100) * 100,
        2,
    )

    if assessed_weight == 100:
        overall_status = "complete"
    elif assessed_weight == 0:
        overall_status = "unassessed"
    else:
        overall_status = "incomplete"

    return {
        "overall_score": overall_score,
        "assessment_completeness": assessment_completeness,
        "status": overall_status,
        "criteria": criteria,
    }
