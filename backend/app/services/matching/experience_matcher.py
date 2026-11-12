from datetime import date, datetime
import re


def parse_employment_date(
    date_value: str | None,
    is_end_date: bool = False,
) -> date | None:

    if not date_value:
        return None

    normalized = date_value.strip().lower()

    if normalized in {"present", "current", "now"}:
        if is_end_date:
            return date.today()

        return None

    date_formats = [
        "%Y-%m-%d",
        "%Y-%m",
        "%b %Y",
        "%B %Y",
        "%m/%Y",
        "%Y",
    ]

    for date_format in date_formats:
        try:
            parsed_date = datetime.strptime(
                date_value.strip(),
                date_format,
            ).date()

            return parsed_date

        except ValueError:
            continue

    return None


def calculate_employment_days(
    start_date: str | None,
    end_date: str | None,
) -> int | None:

    parsed_start = parse_employment_date(start_date)

    parsed_end = parse_employment_date(
        end_date,
        is_end_date=True,
    )

    if parsed_start is None or parsed_end is None:
        return None

    if parsed_end < parsed_start:
        return None

    return (parsed_end - parsed_start).days


def calculate_total_experience_days(
    employment_history: list[dict],
) -> int:
    periods = []

    for employment in employment_history:
        start = parse_employment_date(
            employment.get("start_date")
        )

        end = parse_employment_date(
            employment.get("end_date"),
            is_end_date=True,
        )

        if start is None or end is None:
            continue

        if end < start:
            continue

        periods.append((start, end))

    if not periods:
        return 0

    periods.sort(key=lambda period: period[0])

    merged_periods = []
    current_start, current_end = periods[0]

    for start, end in periods[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            merged_periods.append(
                (current_start, current_end)
            )
            current_start, current_end = start, end

    merged_periods.append((current_start, current_end))

    total_days = sum(
        (end - start).days
        for start, end in merged_periods
    )

    return total_days






EXPERIENCE_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def extract_required_experience_years(
    requirement: str | None,
) -> float | None:

    if not requirement:
        return None

    normalized = requirement.strip().lower()

    pattern = (
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten"
        r"|\d+(?:\.\d+)?)"
        r"\s*\+?\s*(?:years?|yrs?)\b"
    )

    match = re.search(pattern, normalized)

    if not match:
        return None

    value = match.group(1)

    if value in EXPERIENCE_NUMBER_WORDS:
        return float(EXPERIENCE_NUMBER_WORDS[value])

    return float(value)


def assess_experience(
    work_experience: list[dict],
    required_experience: str | None,
) -> dict:

    if not required_experience:
        return {
            "status": "not_required",
            "required_years": None,
            "candidate_experience_days": None,
            "reason": "No experience requirement specified",
        }

    required_years = extract_required_experience_years(
        required_experience
    )

    if required_years is None:
        return {
            "status": "unknown",
            "required_years": None,
            "candidate_experience_days": None,
            "reason": "Could not identify required experience",
        }

    candidate_experience_days = calculate_total_experience_days(
        work_experience
    )

    if candidate_experience_days == 0:
        return {
            "status": "unknown",
            "required_years": required_years,
            "candidate_experience_days": 0,
            "reason": "No reliable employment dates available",
        }

    required_days = required_years * 365.25

    if candidate_experience_days >= required_days:
        status = "met"
    else:
        status = "not_met"

    return {
        "status": status,
        "required_years": required_years,
        "candidate_experience_days": candidate_experience_days,
        "reason": "Candidate experience assessed against job requirement",
    }