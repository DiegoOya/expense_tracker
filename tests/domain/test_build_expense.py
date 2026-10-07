"""Domain rules of add-expense, tested through build_expense."""

from datetime import date

import pytest
from conftest import TODAY, SpyCategorizer, StubCategorizer
from expense_tracker.adapters.fake_categorizer import FakeCategorizer
from expense_tracker.domain.categorizer import Categorizer
from expense_tracker.domain.expenses import build_expense
from expense_tracker.domain.model import (
    CategorySource,
    ExpenseValidationError,
    NewExpense,
)

CATEGORY_ERROR = (
    "category must be one of: food, transport, housing, utilities, "
    "health, leisure, shopping, other"
)


def build(
    *,
    amount: str | int | float | bool = "12.50",
    description: str = "Coffee at Example Cafe",
    date: str | None = "2026-10-01",
    category: str | None = "food",
    categorizer: Categorizer | None = None,
) -> NewExpense:
    """Call build_expense with valid defaults and today = TODAY."""
    return build_expense(
        amount=amount,
        description=description,
        date=date,
        category=category,
        today=TODAY,
        categorizer=categorizer or FakeCategorizer(),
    )


def assert_rejected(message: str, **inputs: object) -> None:
    with pytest.raises(ExpenseValidationError) as excinfo:
        build(**inputs)  # type: ignore[arg-type]
    assert str(excinfo.value) == message


# Date


@pytest.mark.spec("AC-ADD-04")
@pytest.mark.parametrize("given", ["", "   "])
def test_blank_date_defaults_to_today(given: str) -> None:
    assert build(date=given).date == date(2026, 10, 6)


@pytest.mark.spec("AC-ADD-05")
def test_date_equal_to_today_is_accepted() -> None:
    assert build(date="2026-10-06").date == date(2026, 10, 6)


@pytest.mark.spec("AC-ADD-06")
def test_date_after_today_is_rejected() -> None:
    assert_rejected("date cannot be in the future", date="2026-10-07")


@pytest.mark.spec("AC-ADD-07")
@pytest.mark.parametrize("given", ["01/10/2026", "2026-13-01", "20261001"])
def test_malformed_or_impossible_date_is_rejected(given: str) -> None:
    assert_rejected("date must be a valid YYYY-MM-DD date", date=given)


# Category


@pytest.mark.spec("AC-ADD-08")
@pytest.mark.parametrize("given", ["", "   "])
def test_blank_category_is_suggested_by_categorizer(given: str) -> None:
    expense = build(description="Train ticket to Example City", category=given)
    assert expense.category == "transport"
    assert expense.category_source == CategorySource.AUTO


@pytest.mark.spec("AC-ADD-09")
@pytest.mark.parametrize(
    ("categorizer", "description"),
    [
        (FakeCategorizer(), "Gift for Example Person"),
        (StubCategorizer("pets"), "Coffee at Example Cafe"),
    ],
    ids=["suggests-nothing", "suggests-pets"],
)
def test_missing_or_unknown_suggestion_falls_back_to_other(
    categorizer: Categorizer, description: str
) -> None:
    expense = build(
        description=description, category=None, categorizer=categorizer
    )
    assert expense.category == "other"
    assert expense.category_source == CategorySource.AUTO


@pytest.mark.spec("AC-ADD-10")
def test_categorizer_not_called_when_category_given() -> None:
    spy = SpyCategorizer("transport")
    expense = build(category="food", categorizer=spy)
    assert spy.calls == []
    assert expense.category == "food"


@pytest.mark.spec("AC-ADD-11")
def test_category_is_trimmed_and_case_insensitive() -> None:
    expense = build(category="  FOOD ")
    assert expense.category == "food"
    assert expense.category_source == CategorySource.USER


@pytest.mark.spec("AC-ADD-12")
def test_category_outside_list_is_rejected() -> None:
    assert_rejected(CATEGORY_ERROR, category="pets")


@pytest.mark.spec("AC-ADD-13")
def test_categorizer_receives_trimmed_description() -> None:
    spy = SpyCategorizer()
    build(description="  Train ticket  ", category=None, categorizer=spy)
    assert spy.calls == ["Train ticket"]


@pytest.mark.spec("AC-ADD-13")
def test_trimmed_description_is_categorized_by_fake_categorizer() -> None:
    expense = build(description="  Train ticket  ", category=None)
    assert expense.description == "Train ticket"
    assert expense.category == "transport"
    assert expense.category_source == CategorySource.AUTO


# Amount


@pytest.mark.spec("AC-ADD-14")
@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("7", "7.00"),
        (" 12,50 ", "12.50"),
        ("0.01", "0.01"),
        ("1000000.00", "1000000.00"),
    ],
)
def test_valid_amount_is_normalized_to_two_decimals(
    given: str, expected: str
) -> None:
    assert str(build(amount=given).amount) == expected


@pytest.mark.spec("AC-ADD-15")
@pytest.mark.parametrize("given", ["0", "-3.00"])
def test_amount_not_greater_than_zero_is_rejected(given: str) -> None:
    assert_rejected("amount must be greater than 0", amount=given)


@pytest.mark.spec("AC-ADD-16")
def test_amount_above_maximum_is_rejected() -> None:
    assert_rejected("amount must be at most 1000000.00", amount="1000000.01")


@pytest.mark.spec("AC-ADD-17")
@pytest.mark.parametrize(
    "given", ["1.234", "12.500", "1,230", "-1.234", "1000000.001"]
)
def test_amount_with_more_than_two_decimals_is_rejected(given: str) -> None:
    assert_rejected("amount must have at most 2 decimal places", amount=given)


# Description


@pytest.mark.spec("AC-ADD-19")
def test_blank_description_is_rejected() -> None:
    assert_rejected("description must not be empty", description="   ")


@pytest.mark.spec("AC-ADD-20")
@pytest.mark.parametrize(
    "given", ["a" * 201, "  " + "a" * 201 + "  "], ids=["bare", "padded"]
)
def test_description_longer_than_200_is_rejected(given: str) -> None:
    assert_rejected(
        "description must be at most 200 characters", description=given
    )


@pytest.mark.spec("AC-ADD-21")
def test_description_of_200_after_trimming_is_accepted() -> None:
    expense = build(description="  " + "a" * 200 + "  ")
    assert expense.description == "a" * 200


# Validation order


@pytest.mark.spec("AC-ADD-22")
def test_amount_error_is_reported_before_description_error() -> None:
    assert_rejected(
        "amount must be greater than 0", amount="0", description="   "
    )
