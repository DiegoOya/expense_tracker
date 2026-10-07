"""SQLite persistence of expenses."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from conftest import TODAY
from expense_tracker.adapters.fake_categorizer import FakeCategorizer
from expense_tracker.adapters.sqlite_store import SqliteStore
from expense_tracker.domain.expenses import build_expense
from expense_tracker.domain.model import CategorySource, Expense, NewExpense


def coffee() -> NewExpense:
    """The expense of AC-ADD-01."""
    return NewExpense(
        amount=Decimal("12.50"),
        description="Coffee at Example Cafe",
        date=date(2026, 10, 1),
        category="food",
        category_source=CategorySource.USER,
    )


@pytest.mark.spec("AC-ADD-03")
def test_stored_expense_is_read_back_after_reopening(db_path: Path) -> None:
    SqliteStore(db_path).add(coffee())

    reopened = SqliteStore(db_path)

    assert reopened.get(1) == Expense(
        id=1,
        amount=Decimal("12.50"),
        description="Coffee at Example Cafe",
        date=date(2026, 10, 1),
        category="food",
        category_source=CategorySource.USER,
    )


@pytest.mark.spec("AC-ADD-03")
def test_add_returns_the_stored_expense_with_id_1(
    store: SqliteStore,
) -> None:
    stored = store.add(coffee())

    assert stored.id == 1
    assert store.list_all() == [stored]


@pytest.mark.spec("AC-ADD-21")
def test_description_is_stored_without_surrounding_spaces(
    db_path: Path,
) -> None:
    new_expense = build_expense(
        amount="12.50",
        description="  " + "a" * 200 + "  ",
        date="2026-10-01",
        category="food",
        today=TODAY,
        categorizer=FakeCategorizer(),
    )
    SqliteStore(db_path).add(new_expense)

    stored = SqliteStore(db_path).get(1)

    assert stored is not None
    assert stored.description == "a" * 200
