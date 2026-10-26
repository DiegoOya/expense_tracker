"""Value types and constants of the expense domain."""

import calendar
import datetime
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

CATEGORIES: tuple[str, ...] = (
    "food",
    "transport",
    "housing",
    "utilities",
    "health",
    "leisure",
    "shopping",
    "other",
)
FALLBACK_CATEGORY = "other"
CURRENCY = "EUR"
MAX_AMOUNT = Decimal("1000000.00")
MAX_DESCRIPTION_LENGTH = 200
DEFAULT_LIMIT = 50
MAX_LIMIT = 200
MIN_AVERAGE_MONTHS = 2
MAX_AVERAGE_MONTHS = 12


class CategorySource(StrEnum):
    """Who chose the category: the user or the categorizer."""

    USER = "user"
    AUTO = "auto"


@dataclass(frozen=True)
class NewExpense:
    """A validated expense that has not been stored yet.

    `amount` always has exactly 2 decimal places and `description` is
    already trimmed.
    """

    amount: Decimal
    description: str
    date: datetime.date
    category: str
    category_source: CategorySource


@dataclass(frozen=True)
class Expense:
    """A stored expense."""

    id: int
    amount: Decimal
    description: str
    date: datetime.date
    category: str
    category_source: CategorySource


@dataclass(frozen=True)
class ExpenseFilter:
    """Validated filters of a listing.

    Date bounds are inclusive; `category` is lower-case and in
    CATEGORIES; `limit` is between 1 and MAX_LIMIT.
    """

    date_from: datetime.date | None
    date_to: datetime.date | None
    category: str | None
    limit: int


@dataclass(frozen=True)
class ExpensePage:
    """One listing result.

    `expenses` is ordered most recent first and cut to the filter's
    limit; `total_count` counts every match, before the limit.
    """

    expenses: tuple[Expense, ...]
    total_count: int


@dataclass(frozen=True, order=True)
class YearMonth:
    """A calendar month: YearMonth(2026, 10) is "2026-10".

    Ordered by year, then month. `first_day` and `last_day` are only
    called on validated months (from FIRST_MONTH), so they never build
    a date with year 0.
    """

    year: int
    month: int  # 1 to 12

    def previous(self) -> "YearMonth":
        """The month before: 2026-01 -> 2025-12."""
        if self.month == 1:
            return YearMonth(self.year - 1, 12)
        return YearMonth(self.year, self.month - 1)

    def months_before(self, count: int) -> "YearMonth":
        """The month `count` months back: 2026-01, 3 -> 2025-10.

        May land before FIRST_MONTH (even in year 0 or below); the
        caller checks the range before using the result.
        """
        index = self.year * 12 + (self.month - 1) - count
        return YearMonth(index // 12, index % 12 + 1)

    def first_day(self) -> datetime.date:
        return datetime.date(self.year, self.month, 1)

    def last_day(self) -> datetime.date:
        """28, 29, 30 or 31, from the calendar, never a fixed day."""
        days = calendar.monthrange(self.year, self.month)[1]
        return datetime.date(self.year, self.month, days)

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


FIRST_MONTH = YearMonth(1900, 1)


@dataclass(frozen=True)
class ReportRequest:
    """Validated inputs of a monthly report."""

    month: YearMonth
    compare_to: YearMonth
    average_of: int | None = None  # months to average, if asked


@dataclass(frozen=True)
class CategoryShare:
    """One category of the report month."""

    category: str
    total: Decimal  # 2 decimals
    count: int
    percentage: Decimal  # 1 decimal, rounded half-up


@dataclass(frozen=True)
class CategoryDifference:
    """One category of the comparison."""

    category: str
    total: Decimal  # in the compared month, 0.00 if none
    difference: Decimal  # report month minus compared month


@dataclass(frozen=True)
class Comparison:
    """The compared month and the differences with it."""

    month: YearMonth
    total: Decimal
    difference: Decimal
    categories: tuple[CategoryDifference, ...]  # by category name


@dataclass(frozen=True)
class AverageComparison:
    """The average of the months before the report month."""

    months: int  # how many months were averaged
    first_month: YearMonth
    last_month: YearMonth  # the month before the report month
    total: Decimal  # window total / months, half-up to cents
    difference: Decimal  # report month total minus `total`
    # `total` of each item is that category's rounded average.
    categories: tuple[CategoryDifference, ...]  # by category name


@dataclass(frozen=True)
class MonthlyReport:
    """Aggregates of one month and its comparison."""

    month: YearMonth
    total: Decimal
    count: int
    categories: tuple[CategoryShare, ...]  # total desc, then name
    comparison: Comparison
    average: AverageComparison | None = None


class ExpenseValidationError(ValueError):
    """An input broke a rule; `str(error)` is the user message."""
