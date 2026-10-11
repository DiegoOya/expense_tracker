"""MCP server: the imperative shell around the expense domain.

Each tool parses input with the domain, persists with the store and
returns plain data. Domain errors become `ToolError`, the only
exception whose message reaches the client in MCP SDK v2
(docs/adr/0003).
"""

import datetime
import inspect
import os
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from expense_tracker.adapters.fake_categorizer import FakeCategorizer
from expense_tracker.adapters.sqlite_store import SqliteStore
from expense_tracker.domain.categorizer import Categorizer
from expense_tracker.domain.expenses import build_expense
from expense_tracker.domain.filters import build_filter
from expense_tracker.domain.model import (
    CURRENCY,
    Expense,
    ExpenseValidationError,
)

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

    # The SDK sends __doc__ verbatim, indentation included; getdoc()
    # gives the client a clean description.
    for tool in (add_expense, list_expenses):
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


def main() -> None:
    """Entry point for the `expense-tracker-mcp` console script."""
    db_path = Path(os.environ.get("EXPENSE_TRACKER_DB", DEFAULT_DB_PATH))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    server = build_server(
        SqliteStore(db_path), FakeCategorizer(), datetime.date.today
    )
    server.run(transport="stdio")
