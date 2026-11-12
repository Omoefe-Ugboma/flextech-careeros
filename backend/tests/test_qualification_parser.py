
from app.services.matching.qualification_parser import (
    extract_academic_level,
)
from app.services.matching.qualification_parser import (
    extract_academic_field,
)


def test_extract_bachelor_level():
    result = extract_academic_level(
        "Bachelor's degree in Computer Science"
    )

    assert result == "bachelor"


def test_extract_master_level():
    result = extract_academic_level(
        "MSc in Information Technology"
    )

    assert result == "master"


def test_extract_doctorate_level():
    result = extract_academic_level(
        "PhD in Artificial Intelligence"
    )

    assert result == "doctorate"


def test_extract_diploma_level():
    result = extract_academic_level(
        "National Diploma in Software Engineering"
    )

    assert result == "diploma"


def test_extract_certificate_level():
    result = extract_academic_level(
        "Professional Certificate in Python"
    )

    assert result == "certificate"


def test_unrecognised_professional_certification():
    result = extract_academic_level(
        "AWS Certified Solutions Architect"
    )

    assert result is None


def test_extract_computer_science_field():
    result = extract_academic_field(
        "Bachelor's degree in Computer Science"
    )

    assert result == "computer science"


def test_extract_information_technology_field():
    result = extract_academic_field(
        "MSc in Information Technology"
    )

    assert result == "information technology"


def test_extract_artificial_intelligence_field():
    result = extract_academic_field(
        "PhD in Artificial Intelligence"
    )

    assert result == "artificial intelligence"


def test_field_not_specified():
    result = extract_academic_field(
        "Bachelor's degree"
    )

    assert result is None


def test_unspecified_degree_has_no_academic_level():
    result = extract_academic_level(
        "A degree in Computer Science or equivalent experience"
    )

    assert result is None


def test_unspecified_degree_extracts_computer_science_field():
    result = extract_academic_field(
        "A degree in Computer Science or equivalent experience"
    )

    assert result == "computer science"


def test_unspecified_degree_extracts_artificial_intelligence_field():
    result = extract_academic_field(
        "A degree in Artificial Intelligence or equivalent experience"
    )

    assert result == "artificial intelligence"


def test_degree_without_field_returns_no_field():
    result = extract_academic_field(
        "A degree or equivalent experience"
    )

    assert result is None
