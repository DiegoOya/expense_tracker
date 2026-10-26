"""Rules of the monthly report: input validation and aggregation.

Specs: specs/monthly-report/spec.md and
specs/avg-month-comparison/spec.md.

Inputs are checked in the order month (format, before FIRST_MONTH,
future), then compare_to (the same, or, when not given, whether month
has a month before it), then average_of (integer, range, window not
before FIRST_MONTH). Only the first failure is reported.
"""

import datetime
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from expense_tracker.domain.model import (
    FIRST_MONTH,
    MAX_AVERAGE_MONTHS,
    MIN_AVERAGE_MONTHS,
    AverageComparison,
    CategoryDifference,
    CategoryShare,
    Comparison,
    Expense,
    ExpenseValidationError,
    MonthlyReport,
    ReportRequest,
    YearMonth,
)
from expense_tracker.domain.parsing import optional_text, strict_month

COMPARE_TO_REQUIRED = f"compare_to must be given for month {FIRST_MONTH}"
AVERAGE_OF_NOT_INTEGER = "average_of must be an integer"
AVERAGE_OF_OUT_OF_RANGE = (
    f"average_of must be between {MIN_AVERAGE_MONTHS} and {MAX_AVERAGE_MONTHS}"
)
AVERAGE_BEFORE_FIRST_MONTH = f"average_of cannot reach before {FIRST_MONTH}"
ZERO = Decimal("0.00")
CENT = Decimal("0.01")
TENTH = Decimal("0.1")

# Total and number of expenses of one category in one month.
Totals = dict[str, tuple[Decimal, int]]


def build_report_request(
    *,
    month: str | None,
    compare_to: str | None,
    average_of: int | float | str | bool | None = None,
    today: datetime.date,
) -> ReportRequest:
    """Validate the inputs of a report and fill in the defaults.

    `month` defaults to the current month and `compare_to` to the
    month before `month`; `average_of` stays None when not given.
    Raises ExpenseValidationError with the spec message of the first
    rule broken. Pure: `today` is passed in.
    """
    current = YearMonth(today.year, today.month)
    report_month = _optional_month(month, "month", current)
    if report_month is None:
        report_month = current
    compared = _optional_month(compare_to, "compare_to", current)
    if compared is None:
        if report_month == FIRST_MONTH:
            raise ExpenseValidationError(COMPARE_TO_REQUIRED)
        compared = report_month.previous()
    months = _optional_average_of(average_of, report_month)
    return ReportRequest(
        month=report_month, compare_to=compared, average_of=months
    )


def build_report(
    month: YearMonth,
    expenses: Sequence[Expense],
    compare_to: YearMonth,
    compared_expenses: Sequence[Expense],
) -> MonthlyReport:
    """Aggregate the expenses of two months into a report.

    The expenses must belong to their month (the store guarantees it).
    All arithmetic is Decimal: shares are rounded half-up to one
    decimal, each on its own, so they may not add up to 100.0.
    """
    totals = _totals(expenses)
    compared_totals = _totals(compared_expenses)
    month_total = _grand_total(totals)
    compared_total = _grand_total(compared_totals)

    shares = sorted(
        (
            CategoryShare(
                category=category,
                total=total,
                count=count,
                percentage=_share(total, month_total),
            )
            for category, (total, count) in totals.items()
        ),
        key=lambda share: (-share.total, share.category),
    )
    differences = tuple(
        CategoryDifference(
            category=category,
            total=_total_of(compared_totals, category),
            difference=_total_of(totals, category)
            - _total_of(compared_totals, category),
        )
        for category in sorted(totals.keys() | compared_totals.keys())
    )
    return MonthlyReport(
        month=month,
        total=month_total,
        count=sum(count for _, count in totals.values()),
        categories=tuple(shares),
        comparison=Comparison(
            month=compare_to,
            total=compared_total,
            difference=month_total - compared_total,
            categories=differences,
        ),
    )


def build_average(
    month_expenses: Sequence[Expense],
    window_expenses: Sequence[Expense],
    *,
    month: YearMonth,
    months: int,
) -> AverageComparison:
    """Average the `months` months before `month`.

    Empty months count as 0, so every average divides by `months`.
    Each average is rounded half-up to cents on its own, and each
    difference is taken from the rounded value. The window expenses
    must fall inside the window (the store guarantees it).
    """
    totals = _totals(month_expenses)
    window_totals = _totals(window_expenses)
    average = _average(_grand_total(window_totals), months)
    categories = []
    for category in sorted(totals.keys() | window_totals.keys()):
        category_average = _average(_total_of(window_totals, category), months)
        categories.append(
            CategoryDifference(
                category=category,
                total=category_average,
                difference=_total_of(totals, category) - category_average,
            )
        )
    return AverageComparison(
        months=months,
        first_month=month.months_before(months),
        last_month=month.previous(),
        total=average,
        difference=_grand_total(totals) - average,
        categories=tuple(categories),
    )


def _optional_average_of(
    value: int | float | str | bool | None, month: YearMonth
) -> int | None:
    """The validated number of months to average, or None.

    Only a real integer counts: not a bool, a string or a float, even
    one without fraction such as 3.0.
    """
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExpenseValidationError(AVERAGE_OF_NOT_INTEGER)
    if not MIN_AVERAGE_MONTHS <= value <= MAX_AVERAGE_MONTHS:
        raise ExpenseValidationError(AVERAGE_OF_OUT_OF_RANGE)
    if month.months_before(value) < FIRST_MONTH:
        raise ExpenseValidationError(AVERAGE_BEFORE_FIRST_MONTH)
    return value


def _average(total: Decimal, months: int) -> Decimal:
    """`total` over `months`, half-up to cents."""
    return (total / months).quantize(CENT, ROUND_HALF_UP)


def _optional_month(
    value: str | None, name: str, current: YearMonth
) -> YearMonth | None:
    """The validated month, or None when not given.

    `name` ("month" or "compare_to") starts each error message, so
    both inputs follow exactly the same rules.
    """
    text = optional_text(value)
    if text is None:
        return None
    parsed = strict_month(text)
    if parsed is None:
        raise ExpenseValidationError(f"{name} must be a valid YYYY-MM month")
    if parsed < FIRST_MONTH:
        raise ExpenseValidationError(f"{name} cannot be before {FIRST_MONTH}")
    if parsed > current:
        raise ExpenseValidationError(f"{name} cannot be in the future")
    return parsed


def _totals(expenses: Sequence[Expense]) -> Totals:
    totals: Totals = {}
    for expense in expenses:
        total, count = totals.get(expense.category, (ZERO, 0))
        totals[expense.category] = (total + expense.amount, count + 1)
    return totals


def _grand_total(totals: Totals) -> Decimal:
    return sum((total for total, _ in totals.values()), ZERO)


def _total_of(totals: Totals, category: str) -> Decimal:
    return totals.get(category, (ZERO, 0))[0]


def _share(total: Decimal, month_total: Decimal) -> Decimal:
    """Percentage of the month, half-up to one decimal.

    Only called for categories with expenses, so `month_total` is
    never zero.
    """
    return (total * 100 / month_total).quantize(TENTH, ROUND_HALF_UP)
