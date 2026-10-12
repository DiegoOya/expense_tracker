"""Rules of the monthly report: input validation and aggregation.

Spec: specs/monthly-report/spec.md. Inputs are checked in the order
month (format, before FIRST_MONTH, future), then compare_to (the same,
or, when not given, whether month has a month before it). Only the
first failure is reported.
"""

import datetime
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from expense_tracker.domain.model import (
    FIRST_MONTH,
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
ZERO = Decimal("0.00")
TENTH = Decimal("0.1")

# Total and number of expenses of one category in one month.
Totals = dict[str, tuple[Decimal, int]]


def build_report_request(
    *, month: str | None, compare_to: str | None, today: datetime.date
) -> ReportRequest:
    """Validate the inputs of a report and fill in the defaults.

    `month` defaults to the current month and `compare_to` to the
    month before `month`. Raises ExpenseValidationError with the spec
    message of the first rule broken. Pure: `today` is passed in.
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
    return ReportRequest(month=report_month, compare_to=compared)


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
