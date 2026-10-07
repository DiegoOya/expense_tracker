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

from expense_tracker.domain.model import CategorySource, Expense, NewExpense

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

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._path)
        try:
            with connection:  # commit, or roll back on error
                yield connection
        finally:
            connection.close()


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
