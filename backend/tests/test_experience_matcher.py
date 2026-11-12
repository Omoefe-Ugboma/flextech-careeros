import pytest
from datetime import date

import pytest

from app.services.matching.experience_matcher import (
    parse_employment_date,
)
from app.services.matching.experience_matcher import (
    calculate_employment_days,
)


from app.services.matching.experience_matcher import (
    calculate_total_experience_days,
)

from app.services.matching.experience_matcher import (
    extract_required_experience_years,
)

def test_overlapping_employment_periods_are_not_double_counted():
    employment_history = [
        {
            "start_date": "2020-01-01",
            "end_date": "2022-12-31",
        },
        {
            "start_date": "2021-01-01",
            "end_date": "2023-12-31",
        },
    ]

    result = calculate_total_experience_days(employment_history)

    expected = (
        date(2023, 12, 31) - date(2020, 1, 1)
    ).days

    assert result == expected


def test_non_overlapping_employment_periods_are_added():
    employment_history = [
        {
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
        },
        {
            "start_date": "2022-01-01",
            "end_date": "2022-12-31",
        },
    ]

    result = calculate_total_experience_days(employment_history)

    expected = (
        date(2020, 12, 31) - date(2020, 1, 1)
    ).days + (
        date(2022, 12, 31) - date(2022, 1, 1)
    ).days

    assert result == expected


def test_invalid_employment_periods_are_ignored():
    employment_history = [
        {
            "start_date": "2022-01-01",
            "end_date": "2020-01-01",
        },
        {
            "start_date": "unknown",
            "end_date": "2023-01-01",
        },
    ]

    result = calculate_total_experience_days(employment_history)

    assert result == 0


def test_empty_employment_history_returns_zero():
    result = calculate_total_experience_days([])

    assert result == 0

@pytest.mark.parametrize(
    "date_value, expected",
    [
        ("2022-01-15", date(2022, 1, 15)),
        ("2022-01", date(2022, 1, 1)),
        ("Jan 2022", date(2022, 1, 1)),
        ("January 2022", date(2022, 1, 1)),
        ("01/2022", date(2022, 1, 1)),
        ("2022", date(2022, 1, 1)),
    ],
)
def test_parse_valid_employment_dates(date_value, expected):
    result = parse_employment_date(date_value)

    assert result == expected


@pytest.mark.parametrize(
    "date_value",
    [
        None,
        "",
        "unknown",
        "not a date",
        "2022-15",
    ],
)
def test_parse_invalid_employment_dates(date_value):
    result = parse_employment_date(date_value)

    assert result is None


def test_present_end_date_returns_current_date():
    result = parse_employment_date(
        "Present",
        is_end_date=True,
    )

    assert result == date.today()


def test_present_start_date_is_not_accepted():
    result = parse_employment_date(
        "Present",
        is_end_date=False,
    )

    assert result is None
    

def test_calculate_one_year_employment_duration():
    result = calculate_employment_days(
        start_date="2022-01-01",
        end_date="2023-01-01",
    )

    assert result == 365


def test_calculate_employment_duration_with_month_dates():
    result = calculate_employment_days(
        start_date="2022-01",
        end_date="2022-07",
    )

    assert result == 181


def test_calculate_current_employment_duration():
    result = calculate_employment_days(
        start_date="2025-01-01",
        end_date="Present",
    )

    assert result is not None
    assert result > 0


def test_invalid_employment_period_returns_none():
    result = calculate_employment_days(
        start_date="2023-01-01",
        end_date="2022-01-01",
    )

    assert result is None


def test_missing_employment_start_date_returns_none():
    result = calculate_employment_days(
        start_date=None,
        end_date="2023-01-01",
    )

    assert result is None
    



@pytest.mark.parametrize(
    "requirement, expected",
    [
        ("3 years of experience", 3.0),
        ("3+ years of experience", 3.0),
        ("at least 3 years of experience", 3.0),
        ("minimum of three years of experience", 3.0),
        ("two years of backend development", 2.0),
        ("1.5 years of experience", 1.5),
        ("5 yrs experience", 5.0),
    ],
)
def test_extract_required_experience_years(requirement, expected):
    assert extract_required_experience_years(requirement) == expected


@pytest.mark.parametrize(
    "requirement",
    [
        None,
        "",
        "substantial experience",
        "experience is preferred",
        "degree in Computer Science",
    ],
)
def test_unrecognised_experience_requirement_returns_none(requirement):
    assert extract_required_experience_years(requirement) is None

from app.services.matching.experience_matcher import assess_experience


def test_experience_requirement_is_met():
    work_experience = [
        {
            "start_date": "2020-01",
            "end_date": "2025-01",
        }
    ]

    result = assess_experience(
        work_experience=work_experience,
        required_experience="3 years of experience",
    )

    assert result["status"] == "met"
    assert result["required_years"] == 3


def test_experience_requirement_is_not_met():
    work_experience = [
        {
            "start_date": "2023-01",
            "end_date": "2025-01",
        }
    ]

    result = assess_experience(
        work_experience=work_experience,
        required_experience="3 years of experience",
    )

    assert result["status"] == "not_met"


def test_missing_employment_dates_return_unknown():
    work_experience = [
        {
            "start_date": None,
            "end_date": None,
        }
    ]

    result = assess_experience(
        work_experience=work_experience,
        required_experience="3 years of experience",
    )

    assert result["status"] == "unknown"


def test_missing_experience_requirement_returns_not_required():
    result = assess_experience(
        work_experience=[],
        required_experience=None,
    )

    assert result["status"] == "not_required"


def test_unrecognised_experience_requirement_returns_unknown():
    result = assess_experience(
        work_experience=[],
        required_experience="substantial professional experience",
    )

    assert result["status"] == "unknown"