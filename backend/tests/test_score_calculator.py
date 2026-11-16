
from app.services.matching.score_calculator import (
    calculate_match_score,
)

import pytest


def test_calculate_weighted_score_when_all_criteria_are_met():
    match_results = {
        "skills": {
            "required_skills": {
                "required_skill_coverage": 80.0,
            },
        },
        "qualifications": {
            "status": "met",
        },
        "experience": {
            "status": "met",
        },
    }

    result = calculate_match_score(match_results)

    assert result["overall_score"] == 90.0
    assert result["assessment_completeness"] == 100.0
    assert result["status"] == "complete"


def test_unknown_qualification_is_excluded_from_score():
    match_results = {
        "skills": {
            "required_skills": {
                "required_skill_coverage": 80.0,
            },
        },
        "qualifications": {
            "status": "unknown",
        },
        "experience": {
            "status": "met",
        },
    }

    result = calculate_match_score(match_results)

    assert result["overall_score"] == 87.5
    assert result["assessment_completeness"] == 80.0
    assert result["status"] == "incomplete"

    assert result["criteria"]["qualifications"]["weighted_score"] is None
    assert result["criteria"]["qualifications"]["status"] == "unknown"


def test_not_met_qualification_receives_zero_weighted_points():
    match_results = {
        "skills": {
            "required_skills": {
                "required_skill_coverage": 80.0,
            },
        },
        "qualifications": {
            "status": "not_met",
        },
        "experience": {
            "status": "met",
        },
    }

    result = calculate_match_score(match_results)

    assert result["overall_score"] == 70.0
    assert result["assessment_completeness"] == 100.0
    assert result["criteria"]["qualifications"]["weighted_score"] == 0.0


def test_not_required_qualification_is_excluded_from_score():
    match_results = {
        "skills": {
            "required_skills": {
                "required_skill_coverage": 80.0,
            },
        },
        "qualifications": {
            "status": "not_required",
        },
        "experience": {
            "status": "met",
        },
    }

    result = calculate_match_score(match_results)

    assert result["overall_score"] == 87.5
    assert result["assessment_completeness"] == 80.0
    assert result["status"] == "incomplete"

    assert result["criteria"]["qualifications"]["weighted_score"] is None
    assert result["criteria"]["qualifications"]["status"] == "not_required"


def test_returns_no_score_when_all_criteria_are_unassessed():
    match_results = {
        "skills": {
            "required_skills": {
                "required_skill_coverage": None,
            },
        },
        "qualifications": {
            "status": "unknown",
        },
        "experience": {
            "status": "not_required",
        },
    }

    result = calculate_match_score(match_results)

    assert result["overall_score"] is None
    assert result["assessment_completeness"] == 0.0
    assert result["status"] == "unassessed"




@pytest.mark.parametrize("coverage", [-10.0, 120.0])
def test_invalid_skill_coverage_raises_error(coverage):
    match_results = {
        "skills": {
            "required_skills": {
                "required_skill_coverage": coverage,
            },
        },
        "qualifications": {
            "status": "met",
        },
        "experience": {
            "status": "met",
        },
    }

    with pytest.raises(ValueError):
        calculate_match_score(match_results)


def test_no_required_skills_does_not_award_or_deduct_skill_points():
    match_results = {
        "skills": {
            "required_skills": {
                "required_skill_coverage": None,
            },
            "preferred_skills": {
                "matched": ["React"],
                "missing": ["Docker"],
            },
        },
        "qualifications": {
            "status": "met",
        },
        "experience": {
            "status": "met",
        },
    }

    result = calculate_match_score(match_results)

    assert result["overall_score"] == 100.0
    assert result["assessment_completeness"] == 50.0
    assert result["status"] == "incomplete"

    assert result["criteria"]["skills"]["weighted_score"] is None
    assert result["criteria"]["skills"]["status"] == "unknown"

@pytest.mark.parametrize(
    "invalid_coverage",
    [
        True,
        False,
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_invalid_skill_coverage_rejects_boolean_and_non_finite_values(
    invalid_coverage,
):
    match_results = {
        "skills": {
            "required_skills": {
                "required_skill_coverage": invalid_coverage,
            }
        }
    }

    with pytest.raises(
        ValueError,
        match="finite numeric value",
    ):
        calculate_match_score(match_results)