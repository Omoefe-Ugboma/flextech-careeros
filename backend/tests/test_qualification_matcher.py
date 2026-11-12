from app.services.matching.qualification_matcher import (
    compare_qualification_levels,
)

from app.services.matching.qualification_matcher import (
    normalize_qualification,
    normalize_field,
    assess_qualification,
    get_qualification_level,
)


def test_normalize_qualification():
    assert normalize_qualification("BSc") == "bachelor"

    assert (
        normalize_qualification("Bachelor of Science")
        == "bachelor"
    )

    assert normalize_qualification("MSc") == "master"
    
    assert (
    normalize_qualification("Bachelor's degree")
    == "bachelor"
    )

    assert (
        normalize_qualification("Master's degree")
        == "master"
    )


def test_assess_qualification_met():
    education = [
        {
            "qualification": "BSc",
            "field_of_study": "Computer Science",
            "institution": "University Example",
        }
    ]

    result = assess_qualification(
        education,
        "Bachelor's degree",
        "Computer Science",
    )

    assert result["status"] == "met"
    assert len(result["evidence"]) == 1


def test_assess_qualification_unknown_without_education():
    result = assess_qualification(
        [],
        "Bachelor's degree",
        "Computer Science",
    )

    assert result["status"] == "unknown"


def test_assess_qualification_not_met_with_field_mismatch():
    education = [
        {
            "qualification": "BSc",
            "field_of_study": "Accounting",
            "institution": "University Example",
        }
    ]

    result = assess_qualification(
        education,
        "Bachelor's degree",
        "Computer Science",
    )

    assert result["status"] == "not_met"


def test_normalize_field():
    assert normalize_field("Computer Science") == "computer science"

    assert normalize_field("Computer Sciences") == "computer science"

    assert normalize_field("Computing Science") == "computer science"

    assert normalize_field("IT") == "information technology"

def test_assess_qualification_with_field_alias():
    education = [
        {
            "qualification": "BSc",
            "field_of_study": "Computer Sciences",
            "institution": "University Example",
        }
    ]

    result = assess_qualification(
        education,
        "Bachelor's degree",
        "Computer Science",
    )

    assert result["status"] == "met"
    
def test_assess_qualification_unknown_without_field():
    education = [
        {
            "qualification": "BSc",
            "field_of_study": None,
            "institution": "University Example",
        }
    ]

    result = assess_qualification(
        education,
        "Bachelor's degree",
        "Computer Science",
    )

    assert result["status"] == "unknown"

def test_get_qualification_level_bachelor():
    assert get_qualification_level("BSc") == 3


def test_get_qualification_level_master():
    assert get_qualification_level("MSc") == 4


def test_get_qualification_level_unknown():
    assert get_qualification_level(
        "Unknown qualification"
    ) is None


def test_compare_qualification_levels_met():
    result = compare_qualification_levels("MSc", "BSc")

    assert result == "met"


def test_compare_qualification_levels_not_met():
    result = compare_qualification_levels("Diploma", "BSc")

    assert result == "not_met"


def test_compare_qualification_levels_equal():
    result = compare_qualification_levels("BSc", "BSc")

    assert result == "met"


def test_compare_qualification_levels_unknown():
    result = compare_qualification_levels(
        "Unknown qualification",
        "BSc",
    )

    assert result == "unknown"
    
    

def test_assess_qualification_with_multiple_education_records():
    education = [
        {
            "qualification": "Diploma",
            "field_of_study": "Information Technology",
            "institution": "College Example",
        },
        {
            "qualification": "BSc",
            "field_of_study": "Computer Science",
            "institution": "University Example",
        },
        {
            "qualification": "MSc",
            "field_of_study": "Artificial Intelligence",
            "institution": "University of Mauritius",
        },
    ]

    result = assess_qualification(
        education,
        "Bachelor's degree",
        "Computer Science",
    )

    assert result["status"] == "met"
    assert len(result["evidence"]) == 1
    assert result["evidence"][0]["qualification"] == "BSc"



def test_assess_qualification_with_multiple_non_matching_records():
    education = [
        {
            "qualification": "BSc",
            "field_of_study": "Accounting",
            "institution": "University A",
        },
        {
            "qualification": "MSc",
            "field_of_study": "Artificial Intelligence",
            "institution": "University B",
        },
    ]

    result = assess_qualification(
        education,
        "Bachelor's degree",
        "Computer Science",
    )

    assert result["status"] == "not_met"
    assert result["evidence"] == []


