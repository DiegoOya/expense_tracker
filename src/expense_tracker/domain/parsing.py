"""Input rules shared by the tools that take dates and categories.

add_expense and list_expenses both trim optional text, read dates in
strict YYYY-MM-DD form and accept categories case-insensitively. Each
caller keeps its own error messages; these helpers only parse.
"""

import datetime
import re

from expense_tracker.domain.model import CATEGORIES, YearMonth

DATE_TEXT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
MONTH_TEXT = re.compile(r"([0-9]{4})-(0[1-9]|1[0-2])")
UNKNOWN_CATEGORY = "category must be one of: " + ", ".join(CATEGORIES)


def optional_text(value: str | None) -> str | None:
    """Trimmed value, or None when missing, null or blank."""
    if value is None or not value.strip():
        return None
    return value.strip()


def strict_date(text: str) -> datetime.date | None:
    """The date of a strict YYYY-MM-DD text, or None if invalid.

    `fromisoformat` alone also accepts "20261001" and week dates, so
    the shape is checked first.
    """
    if DATE_TEXT.fullmatch(text) is None:
        return None
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


def strict_month(text: str) -> YearMonth | None:
    """The month of a strict YYYY-MM text, or None if invalid.

    ASCII digits only and a month from 01 to 12, so "+2026-10",
    "2026 -10" and full-width digits are invalid. The year is not
    range-checked here: "0000-05" parses and the caller rejects it.
    """
    match = MONTH_TEXT.fullmatch(text)
    if match is None:
        return None
    return YearMonth(int(match.group(1)), int(match.group(2)))


def known_category(text: str) -> str | None:
    """The lower-case category if `text` names one, else None."""
    lowered = text.lower()
    return lowered if lowered in CATEGORIES else None
