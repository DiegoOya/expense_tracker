"""Value types and constants of the expense domain."""

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


class ExpenseValidationError(ValueError):
    """An input broke a rule; `str(error)` is the user message."""
