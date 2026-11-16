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
    # PostgreSQL aliases
    assert normalize_skill("Postgres") == "postgresql"
    assert normalize_skill("PostgreSQL") == "postgresql"

    # React aliases
    assert normalize_skill("ReactJS") == "react"
    assert normalize_skill("React.js") == "react"
    assert normalize_skill("React JS") == "react"

    # Git aliases
    assert normalize_skill("Git/GitHub") == "git"
    assert normalize_skill("Git and GitHub") == "git"
    assert normalize_skill("Git & GitHub") == "git"

    # Preserve unrelated programming languages
    assert normalize_skill("C++") == "c++"
    assert normalize_skill("C") == "c"

    assert normalize_skill("Git/GitHub") == "git"


def test_compare_skills_with_aliases():
    result = compare_skills(
        ["Postgres", "ReactJS", "Python", "Git/GitHub"],
        ["PostgreSQL", "React", "Python", "Git"],
    )

    assert result["matched_skills"] == [
        "git",
        "postgresql",
        "python",
        "react",
    ]

    assert result["missing_skills"] == []
    assert result["extra_skills"] == []


def test_compare_git_alias_with_git_requirement():
    result = compare_skills(
        ["Git/GitHub", "Python"],
        ["Git", "Python"],
    )

    assert result["matched_skills"] == ["git", "python"]
    assert result["missing_skills"] == []
    assert result["extra_skills"] == []


def test_collect_skill_evidence():
    from app.services.matching.skill_matcher import (
        collect_skill_evidence,
    )

    approved_cv = {
        "skills": [
            "Python",
            "FastAPI",
            "Git/GitHub",
        ],
        "projects": [
            {
                "name": "CareerOS",
                "technologies": [
                    "Python",
                    "Postgres",
                    "Git",
                ],
            }
        ],
    }

    result = collect_skill_evidence(approved_cv)

    # Python has two sources of evidence.
    assert len(result["python"]) == 2
    assert result["python"][0]["source"] == "cv_skill"
    assert result["python"][1]["source"] == "project"

    # PostgreSQL is normalized correctly.
    assert result["postgresql"][0]["details"] == "CareerOS"

    # FastAPI is listed directly in the CV.
    assert result["fastapi"][0]["source"] == "cv_skill"

    # Git/GitHub and Git normalize to one skill,
    # while preserving both evidence sources.
    assert len(result["git"]) == 2
    assert result["git"][0]["source"] == "cv_skill"
    assert result["git"][1]["source"] == "project"


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
