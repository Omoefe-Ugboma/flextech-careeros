
SKILL_ALIASES = {
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "reactjs": "react",
    "react.js": "react",
}

def normalize_skill(skill: str) -> str:
    normalized = skill.strip().lower()

    return SKILL_ALIASES.get(normalized, normalized)

def compare_skills(
    candidate_skills: list[str],
    required_skills: list[str],
) -> dict:
    normalized_candidate = {
        normalize_skill(skill)
        for skill in candidate_skills
    }

    normalized_required = {
        normalize_skill(skill)
        for skill in required_skills
    }

    matched = normalized_candidate & normalized_required

    missing = normalized_required - normalized_candidate

    extra = normalized_candidate - normalized_required

    return {
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "extra_skills": sorted(extra),
    }
    

def calculate_skill_coverage(
    matched_skills: list[str],
    required_skills: list[str],
) -> float | None:

    normalized_required = {
        normalize_skill(skill)
        for skill in required_skills
        if skill.strip()
    }

    normalized_matched = {
        normalize_skill(skill)
        for skill in matched_skills
        if skill.strip()
    }

    if not normalized_required:
        return None

    valid_matches = normalized_matched & normalized_required

    coverage = (
        len(valid_matches) / len(normalized_required)
    ) * 100

    return round(coverage, 2)


def collect_skill_evidence(
    approved_cv: dict,
) -> dict:

    evidence = {}

    for skill in approved_cv.get("skills", []):
        normalized_skill = normalize_skill(skill)

        if not normalized_skill:
            continue

        evidence.setdefault(normalized_skill, []).append({
            "source": "cv_skill",
            "details": "Listed in candidate skills",
        })

    for project in approved_cv.get("projects", []):
        project_name = project.get("name")

        for technology in project.get("technologies", []):
            normalized_skill = normalize_skill(technology)

            if not normalized_skill:
                continue

            evidence.setdefault(normalized_skill, []).append({
                "source": "project",
                "details": project_name,
            })

    return evidence

def build_skill_match_result(
    approved_cv: dict,
    required_skills: list[str],
) -> dict:

    evidence = collect_skill_evidence(approved_cv)

    candidate_skills = list(evidence.keys())

    comparison = compare_skills(
        candidate_skills,
        required_skills,
    )

    coverage = calculate_skill_coverage(
        comparison["matched_skills"],
        required_skills,
    )

    matched_evidence = {
        skill: evidence[skill]
        for skill in comparison["matched_skills"]
    }

    return {
        **comparison,
        "required_skill_coverage": coverage,
        "skill_evidence": matched_evidence,
    }
    

def build_preferred_skill_result(
    approved_cv: dict,
    preferred_skills: list[str],
) -> dict:

    evidence = collect_skill_evidence(approved_cv)

    candidate_skills = list(evidence.keys())

    comparison = compare_skills(
        candidate_skills,
        preferred_skills,
    )

    coverage = calculate_skill_coverage(
        comparison["matched_skills"],
        preferred_skills,
    )

    matched_evidence = {
        skill: evidence[skill]
        for skill in comparison["matched_skills"]
    }

    return {
        "matched_preferred_skills": comparison["matched_skills"],
        "missing_preferred_skills": comparison["missing_skills"],
        "preferred_skill_coverage": coverage,
        "preferred_skill_evidence": matched_evidence,
    }
    


def build_complete_skill_match_result(
    approved_cv: dict,
    required_skills: list[str],
    preferred_skills: list[str],
) -> dict:

    required_result = build_skill_match_result(
        approved_cv,
        required_skills,
    )

    preferred_result = build_preferred_skill_result(
        approved_cv,
        preferred_skills,
    )

    return {
        "required_skills": required_result,
        "preferred_skills": preferred_result,
    }
