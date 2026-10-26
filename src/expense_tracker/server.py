"""MCP server: the imperative shell around the expense domain.

Each tool parses input with the domain, persists with the store and
returns plain data. Domain errors become `ToolError`, the only
exception whose message reaches the client in MCP SDK v2
(docs/adr/0003).
"""

import datetime
import inspect
import os
import sys
from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import NotRequired, TypedDict

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from expense_tracker.adapters.sqlite_store import SqliteStore
from expense_tracker.domain.categorizer import Categorizer
from expense_tracker.domain.expenses import build_expense
from expense_tracker.domain.filters import build_filter
from expense_tracker.domain.model import (
    CURRENCY,
    AverageComparison,
    Expense,
    ExpenseValidationError,
    MonthlyReport,
    YearMonth,
)
from expense_tracker.domain.reports import (
    build_average,
    build_report,
    build_report_request,
)
from expense_tracker.startup import ConfigurationError, choose_categorizer

DEFAULT_DB_PATH = "data/expenses.db"


class ExpenseOut(TypedDict):
    """Structured output of a stored expense."""

    id: int
    amount: str
    currency: str
    description: str
    date: str
    category: str
    category_source: str


class ExpenseListOut(TypedDict):
    """Structured output of a listing."""

    expenses: list[ExpenseOut]
    total_count: int


class CategoryShareOut(TypedDict):
    """One category of a monthly report."""

    category: str
    total: str
    count: int
    percentage: str


class CategoryDifferenceOut(TypedDict):
    """One category of a report's comparison."""

    category: str
    total: str
    difference: str


class ComparisonOut(TypedDict):
    """The compared month of a report."""

    month: str
    total: str
    difference: str
    categories: list[CategoryDifferenceOut]


class AverageOut(TypedDict):
    """The average of the months before the report month."""

    months: int
    first_month: str
    last_month: str
    total: str
    difference: str
    categories: list[CategoryDifferenceOut]


class MonthlyReportOut(TypedDict):
    """Structured output of a monthly report."""

    month: str
    currency: str
    total: str
    count: int
    categories: list[CategoryShareOut]
    comparison: ComparisonOut
    average: NotRequired[AverageOut]  # only when average_of is given


def build_server(
    store: SqliteStore,
    categorizer: Categorizer,
    today: Callable[[], datetime.date],
) -> MCPServer:
    """Create the MCP server with its tools bound to these adapters."""
    server = MCPServer("expense-tracker")

    def add_expense(
        amount: str | int | float | bool,
        description: str,
        date: str | None = None,
        category: str | None = None,
    ) -> ExpenseOut:
        """Record one expense in EUR and return it as stored.

        amount: positive, at most 2 decimals, "." or "," as decimal
        separator (e.g. "12.50"), max 1000000.00.
        description: what the expense was, 1-200 characters.
        date: YYYY-MM-DD, not in the future; defaults to today.
        category: one of food, transport, housing, utilities, health,
        leisure, shopping, other; suggested automatically if omitted.
        """
        try:
            new_expense = build_expense(
                amount=amount,
                description=description,
                date=date,
                category=category,
                today=today(),
                categorizer=categorizer,
            )
        except ExpenseValidationError as error:
            raise ToolError(str(error)) from error
        return _to_output(store.add(new_expense))

    def list_expenses(
        date_from: str | None = None,
        date_to: str | None = None,
        category: str | None = None,
        limit: int | float | str | bool | None = None,
    ) -> ExpenseListOut:
        """List stored expenses, most recent first.

        date_from, date_to: YYYY-MM-DD, inclusive bounds, both optional.
        category: one of food, transport, housing, utilities, health,
        leisure, shopping, other; optional.
        limit: integer from 1 to 200, default 50.
        Returns the expenses and total_count, the number of expenses
        that match the filters before the limit is applied.
        """
        try:
            expense_filter = build_filter(
                date_from=date_from,
                date_to=date_to,
                category=category,
                limit=limit,
            )
        except ExpenseValidationError as error:
            raise ToolError(str(error)) from error
        page = store.search(expense_filter)
        return ExpenseListOut(
            expenses=[_to_output(expense) for expense in page.expenses],
            total_count=page.total_count,
        )

    def monthly_report(
        month: str | None = None,
        compare_to: str | None = None,
        average_of: int | float | str | bool | None = None,
    ) -> MonthlyReportOut:
        """Summarise one month of expenses and compare it with another.

        month: YYYY-MM, from 1900-01 to the current month; defaults to
        the current month.
        compare_to: YYYY-MM, the month to compare with; defaults to the
        month before `month`.
        average_of: integer from 2 to 12; also compare with the average
        of that many months right before `month`. Optional.
        Returns the month's total and number of expenses, the total,
        count and percentage of each category, and the differences with
        the compared month ("+" more, "-" less), overall and per
        category. With average_of, an `average` object with the same
        kind of differences against the average month.
        """
        try:
            request = build_report_request(
                month=month,
                compare_to=compare_to,
                average_of=average_of,
                today=today(),
            )
        except ExpenseValidationError as error:
            raise ToolError(str(error)) from error
        month_expenses = _month_expenses(store, request.month)
        report = build_report(
            request.month,
            month_expenses,
            request.compare_to,
            _month_expenses(store, request.compare_to),
        )
        if request.average_of is not None:
            average = build_average(
                month_expenses,
                _window_expenses(store, request.month, request.average_of),
                month=request.month,
                months=request.average_of,
            )
            report = replace(report, average=average)
        return _to_report_output(report)

    # The SDK sends __doc__ verbatim, indentation included; getdoc()
    # gives the client a clean description.
    for tool in (add_expense, list_expenses, monthly_report):
        server.tool(description=inspect.getdoc(tool))(tool)
    return server


def _to_output(expense: Expense) -> ExpenseOut:
    return ExpenseOut(
        id=expense.id,
        amount=str(expense.amount),
        currency=CURRENCY,
        description=expense.description,
        date=expense.date.isoformat(),
        category=expense.category,
        category_source=expense.category_source.value,
    )


def _month_expenses(store: SqliteStore, month: YearMonth) -> list[Expense]:
    return store.between(month.first_day(), month.last_day())


def _window_expenses(
    store: SqliteStore, month: YearMonth, months: int
) -> list[Expense]:
    """The expenses of the `months` months right before `month`."""
    first = month.months_before(months)
    return store.between(first.first_day(), month.previous().last_day())


def _to_report_output(report: MonthlyReport) -> MonthlyReportOut:
    comparison = report.comparison
    output = MonthlyReportOut(
        month=str(report.month),
        currency=CURRENCY,
        total=str(report.total),
        count=report.count,
        categories=[
            CategoryShareOut(
                category=share.category,
                total=str(share.total),
                count=share.count,
                percentage=str(share.percentage),
            )
            for share in report.categories
        ],
        comparison=ComparisonOut(
            month=str(comparison.month),
            total=str(comparison.total),
            difference=_signed(comparison.difference),
            categories=[
                CategoryDifferenceOut(
                    category=item.category,
                    total=str(item.total),
                    difference=_signed(item.difference),
                )
                for item in comparison.categories
            ],
        ),
    )
    if report.average is not None:
        output["average"] = _to_average_output(report.average)
    return output


def _to_average_output(average: AverageComparison) -> AverageOut:
    return AverageOut(
        months=average.months,
        first_month=str(average.first_month),
        last_month=str(average.last_month),
        total=str(average.total),
        difference=_signed(average.difference),
        categories=[
            CategoryDifferenceOut(
                category=item.category,
                total=str(item.total),
                difference=_signed(item.difference),
            )
            for item in average.categories
        ],
    )


def _signed(value: Decimal) -> str:
    """Difference as text: "+28.60", "-730.80", or "0.00" (no sign).

    The zero check comes first because format(..., "+.2f") gives
    "+0.00", and Decimal("-0.00") would print "-0.00".
    """
    if value == 0:
        return "0.00"
    return format(value, "+.2f")


def main() -> None:
    """Entry point for the `expense-tracker-mcp` console script.

    The categorizer is chosen first, so a bad configuration stops the
    server with exit status 1 and only its message on stderr, before
    the database or stdio are touched.
    """
    try:
        categorizer = choose_categorizer(os.environ)
    except ConfigurationError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
    db_path = Path(os.environ.get("EXPENSE_TRACKER_DB", DEFAULT_DB_PATH))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    server = build_server(
        SqliteStore(db_path), categorizer, datetime.date.today
    )
    server.run(transport="stdio")
