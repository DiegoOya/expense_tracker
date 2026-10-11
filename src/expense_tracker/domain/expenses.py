"""Rules for turning raw tool input into a valid new expense.

Spec: specs/add-expense/spec.md. Inputs are checked in the order
amount, description, date, category, and only the first failure is
reported.
"""

import datetime
import re
from decimal import Decimal

from expense_tracker.domain.categorizer import Categorizer
from expense_tracker.domain.model import (
    CATEGORIES,
    FALLBACK_CATEGORY,
    MAX_AMOUNT,
    MAX_DESCRIPTION_LENGTH,
    CategorySource,
    ExpenseValidationError,
    NewExpense,
)
from expense_tracker.domain.parsing import (
    UNKNOWN_CATEGORY,
    known_category,
    optional_text,
    strict_date,
)

# ASCII digits only ([0-9], not \d), optional sign, optional "." or
# "," followed by at least one digit. Group 1 holds the decimals.
AMOUNT_TEXT = re.compile(r"-?[0-9]+(?:[.,]([0-9]+))?")
CENT = Decimal("0.01")

NOT_A_NUMBER = "amount must be a decimal number"
TOO_MANY_DECIMALS = "amount must have at most 2 decimal places"
NOT_POSITIVE = "amount must be greater than 0"
TOO_LARGE = f"amount must be at most {MAX_AMOUNT}"
EMPTY_DESCRIPTION = "description must not be empty"
LONG_DESCRIPTION = (
    f"description must be at most {MAX_DESCRIPTION_LENGTH} characters"
)
INVALID_DATE = "date must be a valid YYYY-MM-DD date"
FUTURE_DATE = "date cannot be in the future"


def build_expense(
    *,
    amount: str | int | float | bool,
    description: str,
    date: str | None,
    category: str | None,
    today: datetime.date,
    categorizer: Categorizer,
) -> NewExpense:
    """Validate and normalise the inputs of one expense.

    Raises ExpenseValidationError with the spec message of the first
    rule broken. The categorizer is only asked when no category is
    given.
    """
    parsed_amount = _parse_amount(amount)
    clean_description = _parse_description(description)
    expense_date = _parse_date(date, today)
    given_category = optional_text(category)

    if given_category is None:
        suggestion = categorizer.suggest(clean_description)
        chosen = suggestion if suggestion in CATEGORIES else None
        return NewExpense(
            amount=parsed_amount,
            description=clean_description,
            date=expense_date,
            category=chosen or FALLBACK_CATEGORY,
            category_source=CategorySource.AUTO,
        )

    known = known_category(given_category)
    if known is None:
        raise ExpenseValidationError(UNKNOWN_CATEGORY)
    return NewExpense(
        amount=parsed_amount,
        description=clean_description,
        date=expense_date,
        category=known,
        category_source=CategorySource.USER,
    )


def _parse_amount(amount: str | int | float | bool) -> Decimal:
    """Return the amount with 2 decimal places, or raise."""
    # bool is a subclass of int, so it must be rejected first.
    if isinstance(amount, bool):
        raise ExpenseValidationError(NOT_A_NUMBER)
    if isinstance(amount, int):
        # Exact and size-independent: str() refuses ints over 4300
        # digits, Decimal(int) does not.
        return _in_range(Decimal(amount))
    # Floats use their shortest round-tripping text (19.99 -> "19.99");
    # never Decimal(float), which yields 19.989999... Exponent forms
    # such as "1e-05" fail the pattern on purpose.
    text = repr(amount) if isinstance(amount, float) else amount.strip()
    match = AMOUNT_TEXT.fullmatch(text)
    if match is None:
        raise ExpenseValidationError(NOT_A_NUMBER)
    if len(match.group(1) or "") > 2:
        raise ExpenseValidationError(TOO_MANY_DECIMALS)
    return _in_range(Decimal(text.replace(",", ".")))


def _in_range(value: Decimal) -> Decimal:
    if value <= 0:
        raise ExpenseValidationError(NOT_POSITIVE)
    if value > MAX_AMOUNT:
        raise ExpenseValidationError(TOO_LARGE)
    return value.quantize(CENT)


def _parse_description(description: str) -> str:
    """Return the trimmed description, or raise."""
    text = description.strip()
    if not text:
        raise ExpenseValidationError(EMPTY_DESCRIPTION)
    if len(text) > MAX_DESCRIPTION_LENGTH:
        raise ExpenseValidationError(LONG_DESCRIPTION)
    return text


def _parse_date(date: str | None, today: datetime.date) -> datetime.date:
    """Return the expense date (today when not given), or raise."""
    text = optional_text(date)
    if text is None:
        return today
    parsed = strict_date(text)
    if parsed is None:
        raise ExpenseValidationError(INVALID_DATE)
    if parsed > today:
        raise ExpenseValidationError(FUTURE_DATE)
    return parsed
