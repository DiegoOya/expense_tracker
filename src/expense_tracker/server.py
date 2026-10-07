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

    # The SDK sends __doc__ verbatim, indentation included; getdoc()
    # gives the client a clean description.
    server.tool(description=inspect.getdoc(add_expense))(add_expense)
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
