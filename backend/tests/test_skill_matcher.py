from app.services.matching.skill_matcher import (
    normalize_skill,
    compare_skills,
    calculate_skill_coverage,
)


def test_normalize_skill():
    result = normalize_skill("  PYTHON  ")

    assert result == "python"


def test_compare_skills():
    result = compare_skills(
        ["Python", "Django", "Git"],
        ["Python", "FastAPI", "Git"],
    )

    assert result["matched_skills"] == ["git", "python"]
    assert result["missing_skills"] == ["fastapi"]
    assert result["extra_skills"] == ["django"]


def test_calculate_skill_coverage():
    result = calculate_skill_coverage(
        ["Python", "Git"],
        ["Python", "FastAPI", "PostgreSQL", "Git"],
    )

    assert result == 50.0


def test_calculate_skill_coverage_with_duplicates():
    result = calculate_skill_coverage(
        ["Python", "Git"],
        ["Python", "Python", "FastAPI", "Git"],
    )

    assert result == 66.67


def test_calculate_skill_coverage_without_requirements():
    result = calculate_skill_coverage(
        ["Python"],
        [],
    )

    assert result is None
    
    
def test_normalize_skill_aliases():
    assert normalize_skill("Postgres") == "postgresql"
    assert normalize_skill("PostgreSQL") == "postgresql"
    assert normalize_skill("ReactJS") == "react"
    assert normalize_skill("React.js") == "react"
    assert normalize_skill("C++") == "c++"
    assert normalize_skill("C") == "c"
    

def test_compare_skills_with_aliases():
    result = compare_skills(
        ["Postgres", "ReactJS", "Python"],
        ["PostgreSQL", "React", "Python"],
    )

    assert result["matched_skills"] == [
        "postgresql",
        "python",
        "react",
    ]

    assert result["missing_skills"] == []
    assert result["extra_skills"] == []
    

def test_collect_skill_evidence():
    from app.services.matching.skill_matcher import (
        collect_skill_evidence,
    )

    approved_cv = {
        "skills": ["Python", "FastAPI"],
        "projects": [
            {
                "name": "CareerOS",
                "technologies": ["Python", "Postgres"],
            }
        ],
    }

    result = collect_skill_evidence(approved_cv)

    assert len(result["python"]) == 2

    assert result["python"][0]["source"] == "cv_skill"
    assert result["python"][1]["source"] == "project"

    assert result["postgresql"][0]["details"] == "CareerOS"
    assert result["fastapi"][0]["source"] == "cv_skill"
    

def test_build_skill_match_result():
    from app.services.matching.skill_matcher import (
        build_skill_match_result,
    )

    approved_cv = {
        "skills": ["Python", "FastAPI"],
        "projects": [
            {
                "name": "CareerOS",
                "technologies": ["Python", "Postgres"],
            }
        ],
    }

    required_skills = [
        "Python",
        "PostgreSQL",
        "Git",
    ]

    result = build_skill_match_result(
        approved_cv,
        required_skills,
    )

    assert result["matched_skills"] == [
        "postgresql",
        "python",
    ]

    assert result["missing_skills"] == ["git"]

    assert result["required_skill_coverage"] == 66.67

    assert "python" in result["skill_evidence"]
    assert "postgresql" in result["skill_evidence"]

    assert len(result["skill_evidence"]["python"]) == 2
    
def test_build_preferred_skill_result():
    from app.services.matching.skill_matcher import (
        build_preferred_skill_result,
    )

    approved_cv = {
        "skills": ["Python", "Git", "Docker"],
        "projects": [],
    }

    preferred_skills = ["Docker", "AWS"]

    result = build_preferred_skill_result(
        approved_cv,
        preferred_skills,
    )

    assert result["matched_preferred_skills"] == ["docker"]

    assert result["missing_preferred_skills"] == ["aws"]

    assert result["preferred_skill_coverage"] == 50.0



def test_build_complete_skill_match_result():
    from app.services.matching.skill_matcher import (
        build_complete_skill_match_result,
    )

    approved_cv = {
        "skills": ["Python", "Git", "Docker"],
        "projects": [],
    }

    result = build_complete_skill_match_result(
        approved_cv,
        required_skills=["Python", "SQL", "Git"],
        preferred_skills=["Docker", "AWS"],
    )

    assert (
        result["required_skills"]["required_skill_coverage"]
        == 66.67
    )

    assert (
        result["preferred_skills"]["preferred_skill_coverage"]
        == 50.0
    )

    assert result["required_skills"]["missing_skills"] == ["sql"]

    assert (
        result["preferred_skills"]["missing_preferred_skills"]
        == ["aws"]
    )
