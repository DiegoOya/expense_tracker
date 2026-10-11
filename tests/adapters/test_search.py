"""Listing expenses from SQLite: search with a validated filter."""

import pytest

from expense_tracker.adapters.sqlite_store import SqliteStore
from expense_tracker.domain.filters import build_filter
from expense_tracker.domain.model import ExpensePage

ALL_IDS = [5, 4, 3, 2, 6, 1]


def search(
    store: SqliteStore,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    category: str | None = None,
    limit: int | None = None,
) -> ExpensePage:
    return store.search(
        build_filter(
            date_from=date_from,
            date_to=date_to,
            category=category,
            limit=limit,
        )
    )


def ids_of(page: ExpensePage) -> list[int]:
    return [expense.id for expense in page.expenses]


@pytest.mark.spec("AC-LST-02")
def test_empty_database_gives_an_empty_page(store: SqliteStore) -> None:
    page = search(store)

    assert list(page.expenses) == []
    assert page.total_count == 0


@pytest.mark.spec("AC-LST-02")
def test_category_without_matches_gives_an_empty_page(
    dataset: SqliteStore,
) -> None:
    page = search(dataset, category="health")

    assert list(page.expenses) == []
    assert page.total_count == 0


@pytest.mark.spec("AC-LST-03")
@pytest.mark.parametrize(
    ("date_from", "date_to", "expected_ids"),
    [
        ("2026-10-01", None, [5, 4, 3, 2]),
        (" 2026-10-01 ", None, [5, 4, 3, 2]),
        (None, "2026-10-01", [3, 2, 6, 1]),
        ("2026-10-01", "2026-10-03", [4, 3, 2]),
        ("2026-10-01", "2026-10-01", [3, 2]),
        (None, "2026-12-31", [5, 4, 3, 2, 6, 1]),
    ],
    ids=[
        "from",
        "from-with-spaces",
        "to",
        "from-and-to",
        "single-day",
        "to-after-today",
    ],
)
def test_date_bounds_are_inclusive_and_ordered_most_recent_first(
    dataset: SqliteStore,
    date_from: str | None,
    date_to: str | None,
    expected_ids: list[int],
) -> None:
    page = search(dataset, date_from=date_from, date_to=date_to)

    assert ids_of(page) == expected_ids
    assert page.total_count == len(expected_ids)


@pytest.mark.spec("AC-LST-04")
@pytest.mark.parametrize("category", ["food", " FOOD "])
def test_category_filter_ignores_case_and_surrounding_spaces(
    dataset: SqliteStore, category: str
) -> None:
    page = search(dataset, category=category)

    assert ids_of(page) == [4, 2]
    assert page.total_count == 2


@pytest.mark.spec("AC-LST-05")
def test_date_and_category_filters_are_combined(
    dataset: SqliteStore,
) -> None:
    page = search(dataset, date_from="2026-10-02", category="food")

    assert ids_of(page) == [4]
    assert page.total_count == 1


@pytest.mark.spec("AC-LST-06")
@pytest.mark.parametrize("blank", ["", "   "], ids=["empty", "spaces"])
@pytest.mark.parametrize("name", ["date_from", "date_to", "category"], ids=str)
def test_blank_filter_means_not_given(
    dataset: SqliteStore, name: str, blank: str
) -> None:
    page = search(dataset, **{name: blank})  # type: ignore[arg-type]

    assert ids_of(page) == ALL_IDS
    assert page.total_count == 6


@pytest.mark.spec("AC-LST-07")
def test_limit_cuts_the_list_but_not_the_total_count(
    dataset: SqliteStore,
) -> None:
    page = search(dataset, limit=2)

    assert ids_of(page) == [5, 4]
    assert page.total_count == 6


@pytest.mark.spec("AC-LST-09")
@pytest.mark.parametrize("limit", [1, 200])
def test_limit_bounds_return_that_many_of_201_expenses(
    many_expenses: SqliteStore, limit: int
) -> None:
    page = search(many_expenses, limit=limit)

    # All expenses share one date, so the newest ids come first.
    assert ids_of(page) == list(range(201, 201 - limit, -1))
    assert page.total_count == 201
