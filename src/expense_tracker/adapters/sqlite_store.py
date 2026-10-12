"""SQLite persistence for expenses (docs/adr/0002).

Amounts are stored as integer cents. Each operation opens its own
connection: MCPServer runs sync tools in worker threads, and a
`sqlite3` connection may only be used by the thread that created it.
"""

import datetime
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from expense_tracker.domain.model import (
    CategorySource,
    Expense,
    ExpenseFilter,
    ExpensePage,
    NewExpense,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY,
    amount_cents INTEGER NOT NULL,
    description TEXT NOT NULL,
    date TEXT NOT NULL,
    category TEXT NOT NULL,
    category_source TEXT NOT NULL
)
"""
COLUMNS = "id, amount_cents, description, date, category, category_source"

Row = tuple[int, int, str, str, str, str]


class SqliteStore:
    """Stores and reads expenses in one SQLite file."""

    def __init__(self, path: Path) -> None:
        self._path = path
        with self._connection() as connection:
            connection.execute(SCHEMA)

    def add(self, expense: NewExpense) -> Expense:
        with self._connection() as connection:
            cursor = connection.execute(
                "INSERT INTO expenses (amount_cents, description, date,"
                " category, category_source) VALUES (?, ?, ?, ?, ?)",
                (
                    _to_cents(expense.amount),
                    expense.description,
                    expense.date.isoformat(),
                    expense.category,
                    expense.category_source.value,
                ),
            )
            expense_id = cursor.lastrowid
        if expense_id is None:  # pragma: no cover - sqlite always sets it
            raise RuntimeError("SQLite did not return the new expense id")
        return Expense(
            id=expense_id,
            amount=expense.amount,
            description=expense.description,
            date=expense.date,
            category=expense.category,
            category_source=expense.category_source,
        )

    def get(self, expense_id: int) -> Expense | None:
        with self._connection() as connection:
            row = connection.execute(
                f"SELECT {COLUMNS} FROM expenses WHERE id = ?",
                (expense_id,),
            ).fetchone()
        return None if row is None else _to_expense(row)

    def list_all(self) -> list[Expense]:
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT {COLUMNS} FROM expenses ORDER BY id"
            ).fetchall()
        return [_to_expense(row) for row in rows]

    def search(self, expense_filter: ExpenseFilter) -> ExpensePage:
        """Expenses matching the filter, most recent first.

        Ordered by date, then id, both descending. `total_count` counts
        every match; the page is cut to `expense_filter.limit`.
        """
        where, values = _where(expense_filter)
        with self._connection() as connection:
            total: int = connection.execute(
                f"SELECT COUNT(*) FROM expenses{where}", values
            ).fetchone()[0]
            rows = connection.execute(
                f"SELECT {COLUMNS} FROM expenses{where}"
                " ORDER BY date DESC, id DESC LIMIT ?",
                (*values, expense_filter.limit),
            ).fetchall()
        return ExpensePage(
            expenses=tuple(_to_expense(row) for row in rows),
            total_count=total,
        )

    def between(
        self, first: datetime.date, last: datetime.date
    ) -> list[Expense]:
        """Expenses dated from `first` to `last`, both inclusive.

        Ordered by date, then id. Dates are ISO text, so comparing the
        text compares the dates; both bounds are bound parameters.
        """
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT {COLUMNS} FROM expenses"
                " WHERE date >= ? AND date <= ? ORDER BY date, id",
                (first.isoformat(), last.isoformat()),
            ).fetchall()
        return [_to_expense(row) for row in rows]

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._path)
        try:
            with connection:  # commit, or roll back on error
                yield connection
        finally:
            connection.close()


def _where(expense_filter: ExpenseFilter) -> tuple[str, list[str]]:
    """The WHERE clause of a filter and the values to bind to it.

    Only fixed clause text and "?" placeholders go into the SQL; the
    filter's values are always bound, never formatted in. Dates are
    ISO text, so comparing the text compares the dates.
    """
    clauses: list[str] = []
    values: list[str] = []
    if expense_filter.date_from is not None:
        clauses.append("date >= ?")
        values.append(expense_filter.date_from.isoformat())
    if expense_filter.date_to is not None:
        clauses.append("date <= ?")
        values.append(expense_filter.date_to.isoformat())
    if expense_filter.category is not None:
        clauses.append("category = ?")
        values.append(expense_filter.category)
    if not clauses:
        return "", values
    return " WHERE " + " AND ".join(clauses), values


def _to_cents(amount: Decimal) -> int:
    return int(amount.scaleb(2))


def _from_cents(cents: int) -> Decimal:
    # scaleb keeps 2 decimal places: 1250 -> Decimal("12.50").
    return Decimal(cents).scaleb(-2)


def _to_expense(row: Row) -> Expense:
    expense_id, cents, description, date, category, source = row
    return Expense(
        id=expense_id,
        amount=_from_cents(cents),
        description=description,
        date=datetime.date.fromisoformat(date),
        category=category,
        category_source=CategorySource(source),
    )
