"""Rules for turning raw list_expenses input into a valid filter.

Spec: specs/list-expenses/spec.md. Inputs are checked in the order
date_from, date_to, date range, category, limit, and only the first
failure is reported.
"""

import datetime

from expense_tracker.domain.model import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    ExpenseFilter,
    ExpenseValidationError,
)
from expense_tracker.domain.parsing import (
    UNKNOWN_CATEGORY,
    known_category,
    optional_text,
    strict_date,
)

INVALID_DATE_FROM = "date_from must be a valid YYYY-MM-DD date"
INVALID_DATE_TO = "date_to must be a valid YYYY-MM-DD date"
INVALID_RANGE = "date_from must not be after date_to"
LIMIT_NOT_INTEGER = "limit must be an integer"
LIMIT_OUT_OF_RANGE = f"limit must be between 1 and {MAX_LIMIT}"


def build_filter(
    *,
    date_from: str | None,
    date_to: str | None,
    category: str | None,
    limit: int | float | str | bool | None,
) -> ExpenseFilter:
    """Validate and normalise the inputs of one listing.

    Raises ExpenseValidationError with the spec message of the first
    rule broken. Blank, null and missing filters mean "not given".
    """
    start = _optional_date(date_from, INVALID_DATE_FROM)
    end = _optional_date(date_to, INVALID_DATE_TO)
    if start is not None and end is not None and start > end:
        raise ExpenseValidationError(INVALID_RANGE)
    chosen_category = _optional_category(category)
    chosen_limit = _parse_limit(limit)
    return ExpenseFilter(
        date_from=start,
        date_to=end,
        category=chosen_category,
        limit=chosen_limit,
    )


def _optional_date(value: str | None, message: str) -> datetime.date | None:
    text = optional_text(value)
    if text is None:
        return None
    parsed = strict_date(text)
    if parsed is None:
        raise ExpenseValidationError(message)
    return parsed


def _optional_category(value: str | None) -> str | None:
    text = optional_text(value)
    if text is None:
        return None
    known = known_category(text)
    if known is None:
        raise ExpenseValidationError(UNKNOWN_CATEGORY)
    return known


def _parse_limit(limit: int | float | str | bool | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    # bool is a subclass of int, so it is rejected first; strings and
    # numbers with a decimal point (even 10.0) are not integers.
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ExpenseValidationError(LIMIT_NOT_INTEGER)
    if not 1 <= limit <= MAX_LIMIT:
        raise ExpenseValidationError(LIMIT_OUT_OF_RANGE)
    return limit
