"""Domain rules of list-expenses, tested through build_filter."""

import pytest
from expense_tracker.domain.filters import build_filter

from expense_tracker.domain.model import ExpenseValidationError

CATEGORY_ERROR = (
    "category must be one of: food, transport, housing, utilities, "
    "health, leisure, shopping, other"
)
DATE_FROM_ERROR = "date_from must be a valid YYYY-MM-DD date"
DATE_TO_ERROR = "date_to must be a valid YYYY-MM-DD date"
RANGE_ERROR = "date_from must not be after date_to"
LIMIT_RANGE_ERROR = "limit must be between 1 and 200"

BAD_DATES = ["01/10/2026", "2026-13-01", "20261001"]


def assert_rejected(message: str, **inputs: object) -> None:
    """build_filter with valid defaults must fail with `message`."""
    arguments: dict[str, object] = {
        "date_from": None,
        "date_to": None,
        "category": None,
        "limit": None,
    }
    arguments.update(inputs)
    with pytest.raises(ExpenseValidationError) as excinfo:
        build_filter(**arguments)  # type: ignore[arg-type]
    assert str(excinfo.value) == message


@pytest.mark.spec("AC-LST-10")
@pytest.mark.parametrize("date_from", BAD_DATES)
def test_invalid_date_from_is_rejected(date_from: str) -> None:
    assert_rejected(DATE_FROM_ERROR, date_from=date_from)


@pytest.mark.spec("AC-LST-11")
@pytest.mark.parametrize("date_to", BAD_DATES)
def test_invalid_date_to_is_rejected(date_to: str) -> None:
    assert_rejected(DATE_TO_ERROR, date_to=date_to)


@pytest.mark.spec("AC-LST-12")
def test_date_from_after_date_to_is_rejected() -> None:
    assert_rejected(RANGE_ERROR, date_from="2026-10-05", date_to="2026-10-01")


@pytest.mark.spec("AC-LST-13")
def test_unknown_category_is_rejected() -> None:
    assert_rejected(CATEGORY_ERROR, category="pets")


@pytest.mark.spec("AC-LST-14")
@pytest.mark.parametrize("limit", [0, -1, 201])
def test_limit_out_of_range_is_rejected(limit: int) -> None:
    assert_rejected(LIMIT_RANGE_ERROR, limit=limit)


@pytest.mark.spec("AC-LST-16")
@pytest.mark.parametrize(
    ("inputs", "message"),
    [
        ({"date_from": "x", "date_to": "y"}, DATE_FROM_ERROR),
        ({"date_to": "y", "category": "pets"}, DATE_TO_ERROR),
        (
            {
                "date_from": "2026-10-05",
                "date_to": "2026-10-01",
                "category": "pets",
            },
            RANGE_ERROR,
        ),
        ({"category": "pets", "limit": 0}, CATEGORY_ERROR),
    ],
    ids=[
        "date-from-before-date-to",
        "date-to-before-category",
        "range-before-category",
        "category-before-limit",
    ],
)
def test_only_the_first_failure_in_validation_order_is_reported(
    inputs: dict[str, object], message: str
) -> None:
    assert_rejected(message, **inputs)
