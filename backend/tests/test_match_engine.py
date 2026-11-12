
from app.services.matching.match_engine import (
    build_complete_match_result,
)
from app.services.matching.match_engine import (
    build_complete_match_result,
    build_qualification_match_result,
)

def test_complete_match_with_matching_education():
    approved_cv = {
        "skills": ["Python", "FastAPI"],
        "education": [
            {
                "qualification": "BSc",
                "field_of_study": "Computer Science",
                "institution": "Example University",
            }
        ],
        "projects": [],
    }

    job_data = {
        "required_skills": ["Python", "FastAPI"],
        "preferred_skills": ["React"],
        "qualifications": [
            "Bachelor's degree in Computer Science"
        ],
    }

    result = build_complete_match_result(
        approved_cv,
        job_data,
    )

    assert result["skills"]["required_skills"]["required_skill_coverage"] == 100.0
    assert result["qualifications"]["status"] == "met"


def test_qualification_field_mismatch():
    approved_cv = {
        "skills": ["Python"],
        "education": [
            {
                "qualification": "BSc",
                "field_of_study": "Accounting",
                "institution": "Example University",
            }
        ],
        "projects": [],
    }

    job_data = {
        "required_skills": ["Python"],
        "preferred_skills": [],
        "qualifications": [
            "Bachelor's degree in Computer Science"
        ],
    }

    result = build_complete_match_result(
        approved_cv,
        job_data,
    )

    assert result["qualifications"]["status"] == "not_met"


def test_qualification_not_required():
    approved_cv = {
        "skills": ["Python"],
        "education": [],
        "projects": [],
    }

    job_data = {
        "required_skills": ["Python"],
        "preferred_skills": [],
        "qualifications": [],
    }

    result = build_complete_match_result(
        approved_cv,
        job_data,
    )

    assert result["qualifications"]["status"] == "not_required"


def test_missing_education_returns_unknown():
    approved_cv = {
        "skills": ["Python"],
        "education": [],
        "projects": [],
    }

    job_data = {
        "required_skills": ["Python"],
        "preferred_skills": [],
        "qualifications": [
            "Bachelor's degree in Computer Science"
        ],
    }

    result = build_complete_match_result(
        approved_cv,
        job_data,
    )

    assert result["qualifications"]["status"] == "unknown"


def test_multiple_qualification_requirements_require_all_to_be_met():

    approved_cv = {
        "education": [
            {
                "qualification": "BSc",
                "field_of_study": "Computer Science",
                "institution": "Example University",
            }
        ]
    }

    job_data = {
        "required_skills": [],
        "preferred_skills": [],
        "qualifications": [
            "Bachelor's degree in Computer Science",
            "Master's degree in Artificial Intelligence",
        ],
    }

    result = build_complete_match_result(
        approved_cv,
        job_data,
    )

    assert result["qualifications"]["status"] == "not_met"
    


def test_unspecified_degree_and_equivalent_experience_are_separate():
    approved_cv = {
        "education": [
            {
                "qualification": "Bachelor's degree",
                "field_of_study": "Computer Science",
                "institution": "Example University",
            }
        ]
    }

    result = build_qualification_match_result(
        approved_cv=approved_cv,
        qualifications=[
            "A degree in Computer Science or equivalent experience"
        ],
    )

    requirement = result["requirements"][0]

    assert requirement["academic_requirement"] == {
        "status": "unknown",
        "required_level": None,
        "required_field": "computer science",
    }

    assert requirement["equivalent_experience"] == {
        "status": "not_assessed",
    }

def test_complete_match_includes_experience_assessment():
    approved_cv = {
        "skills": ["Python", "FastAPI"],
        "education": [
            {
                "qualification": "Bachelor's degree",
                "field_of_study": "Computer Science",
                "institution": "Example University",
            }
        ],
        "work_experience": [
            {
                "job_title": "Python Developer",
                "company": "Example Company",
                "start_date": "2020-01",
                "end_date": "2025-01",
                "responsibilities": [],
            }
        ],
    }

    job_data = {
        "required_skills": ["Python", "FastAPI"],
        "preferred_skills": ["React"],
        "qualifications": [
            "Bachelor's degree in Computer Science"
        ],
        "experience_requirement": "3 years of experience",
    }

    result = build_complete_match_result(
        approved_cv=approved_cv,
        job_data=job_data,
    )

    assert result["skills"]["required_skills"][
        "required_skill_coverage"
    ] == 100.0

    assert result["qualifications"]["status"] == "met"

    assert result["experience"]["status"] == "met"
    assert result["experience"]["required_years"] == 3