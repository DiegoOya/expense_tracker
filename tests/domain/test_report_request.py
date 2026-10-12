"""Monthly-report input rules, tested through build_report_request."""

from datetime import date

import pytest

from expense_tracker.domain.model import ExpenseValidationError
from expense_tracker.domain.reports import build_report_request

# Spec: unless stated, today = 2026-10-15.
TODAY = date(2026, 10, 15)

MONTH_FORMAT_ERROR = "month must be a valid YYYY-MM month"
MONTH_FUTURE_ERROR = "month cannot be in the future"
MONTH_BEFORE_ERROR = "month cannot be before 1900-01"
COMPARE_FORMAT_ERROR = "compare_to must be a valid YYYY-MM month"
COMPARE_BEFORE_ERROR = "compare_to cannot be before 1900-01"
COMPARE_REQUIRED_ERROR = "compare_to must be given for month 1900-01"

# The year 2026 in full-width digits (U+FF10 is FULLWIDTH DIGIT ZERO),
# then an ASCII "-10". Built with chr() so no tool rewrites it.
FULL_WIDTH_MONTH = (
    "".join(chr(0xFF10 + int(digit)) for digit in "2026") + "-10"
)


def assert_rejected(
    message: str,
    *,
    month: str | None = None,
    compare_to: str | None = None,
) -> None:
    """build_report_request must fail with exactly `message`."""
    with pytest.raises(ExpenseValidationError) as excinfo:
        build_report_request(month=month, compare_to=compare_to, today=TODAY)
    assert str(excinfo.value) == message


@pytest.mark.spec("AC-RPT-13")
@pytest.mark.parametrize(
    "month",
    [
        "2026-13",
        "2026-00",
        "2026-1",
        "10-2026",
        "2026/10",
        "2026-10-01",
        "abc",
        "+2026-10",
        "2026 -10",
        FULL_WIDTH_MONTH,
    ],
    ids=[
        "month-13",
        "month-00",
        "one-digit-month",
        "month-first",
        "slash",
        "full-date",
        "letters",
        "plus-sign",
        "inner-space",
        "full-width-digits",
    ],
)
def test_month_with_invalid_format_is_rejected(month: str) -> None:
    assert_rejected(MONTH_FORMAT_ERROR, month=month)


@pytest.mark.spec("AC-RPT-14")
@pytest.mark.parametrize("month", ["2026-11", "2027-01"])
def test_month_in_the_future_is_rejected(month: str) -> None:
    assert_rejected(MONTH_FUTURE_ERROR, month=month)


@pytest.mark.spec("AC-RPT-15")
@pytest.mark.parametrize("compare_to", ["2026-13", "2026-1", "abc"])
def test_compare_to_with_invalid_format_is_rejected(compare_to: str) -> None:
    assert_rejected(COMPARE_FORMAT_ERROR, compare_to=compare_to)


@pytest.mark.spec("AC-RPT-17")
def test_first_month_without_compare_to_is_rejected() -> None:
    assert_rejected(COMPARE_REQUIRED_ERROR, month="1900-01")


@pytest.mark.spec("AC-RPT-18")
@pytest.mark.parametrize(
    ("month", "compare_to", "message"),
    [
        ("2026-13", "abc", MONTH_FORMAT_ERROR),
        ("1899-12", "abc", MONTH_BEFORE_ERROR),
        ("2026-11", "abc", MONTH_FUTURE_ERROR),
    ],
    ids=["month-format-first", "month-before-first", "month-future-first"],
)
def test_only_the_first_failure_in_validation_order_is_reported(
    month: str, compare_to: str, message: str
) -> None:
    assert_rejected(message, month=month, compare_to=compare_to)


@pytest.mark.spec("AC-RPT-19")
@pytest.mark.parametrize("month", ["1899-12", "0000-05"])
def test_month_before_1900_01_is_rejected(month: str) -> None:
    assert_rejected(MONTH_BEFORE_ERROR, month=month)


@pytest.mark.spec("AC-RPT-20")
def test_compare_to_before_1900_01_is_rejected() -> None:
    assert_rejected(COMPARE_BEFORE_ERROR, compare_to="1899-12")
