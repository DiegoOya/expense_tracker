"""Shared fixtures and test doubles for the expense tracker tests.

Production code is imported at the top, like in any module. The one
exception is a red step: a fixture that needs a module the current
feature has not created yet imports it inside the fixture, so the
missing module only breaks the tests that use it. Move that import up
once the module exists.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from mcp.server.mcpserver import MCPServer

from expense_tracker.adapters.fake_categorizer import FakeCategorizer
from expense_tracker.adapters.sqlite_store import SqliteStore
from expense_tracker.domain.model import CategorySource, NewExpense
from expense_tracker.server import build_server

# Fixed "today" for every test (spec: today = 2026-10-06).
TODAY = date(2026, 10, 6)


class StubCategorizer:
    """Categorizer that always suggests the same value."""

    def __init__(self, suggestion: str | None) -> None:
        self.suggestion = suggestion

    def suggest(self, description: str) -> str | None:
        return self.suggestion


class SpyCategorizer:
    """Categorizer that records every description it receives."""

    def __init__(self, suggestion: str | None = None) -> None:
        self.suggestion = suggestion
        self.calls: list[str] = []

    def suggest(self, description: str) -> str | None:
        self.calls.append(description)
        return self.suggestion


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "expenses.db"


@pytest.fixture
def store(db_path: Path) -> SqliteStore:
    return SqliteStore(db_path)


@pytest.fixture
def server(store: SqliteStore) -> MCPServer:
    return build_server(store, FakeCategorizer(), lambda: TODAY)


@pytest.fixture
def dataset(store: SqliteStore) -> SqliteStore:
    """Store the six expenses of the list-expenses spec, in its order.

    Ids are 1 to 6. Id 6 is stored last but dated 2026-09-30, so the
    date order (5, 4, 3, 2, 6, 1) differs from the id order.
    """
    rows = [
        ("2026-09-28", "750.00", "Rent for September", "housing"),
        ("2026-10-01", "3.50", "Coffee at Example Cafe", "food"),
        (
            "2026-10-01",
            "12.80",
            "Train ticket to Example City",
            "transport",
        ),
        ("2026-10-03", "45.10", "Groceries at Example Market", "food"),
        ("2026-10-05", "9.00", "Cinema at Example Plaza", "leisure"),
        ("2026-09-30", "31.20", "Water bill for September", "utilities"),
    ]
    for day, amount, description, category in rows:
        store.add(
            NewExpense(
                amount=Decimal(amount),
                description=description,
                date=date.fromisoformat(day),
                category=category,
                category_source=CategorySource.USER,
            )
        )
    return store


@pytest.fixture
def many_expenses(store: SqliteStore) -> SqliteStore:
    """Store 201 expenses (ids 1 to 201), all dated 2026-10-01."""
    for number in range(1, 202):
        store.add(
            NewExpense(
                amount=Decimal("1.00"),
                description=f"Example expense {number}",
                date=date(2026, 10, 1),
                category="other",
                category_source=CategorySource.USER,
            )
        )
    return store


@pytest.fixture
def report_server(store: SqliteStore) -> MCPServer:
    """Server whose clock says today is 2026-10-15 (monthly-report)."""
    return build_server(store, FakeCategorizer(), lambda: date(2026, 10, 15))


@pytest.fixture
def report_dataset(store: SqliteStore) -> SqliteStore:
    """Store the sixteen expenses of the monthly-report spec."""
    rows = [
        ("2024-02-29", "8.00", "Taxi to Example Airport", "transport"),
        ("2025-10-10", "40.00", "Dinner at Example Restaurant", "food"),
        ("2025-12-31", "25.00", "New Year dinner at Example Bistro", "food"),
        ("2026-04-10", "0.29", "Chewing gum at Example Kiosk", "food"),
        ("2026-04-11", "3.71", "Bus ticket to Example Town", "transport"),
        ("2026-07-05", "1.00", "Coffee at Example Kiosk", "food"),
        ("2026-07-20", "15.00", "Gift for Example Person", "other"),
        ("2026-08-03", "10.00", "Pharmacy at Example Street", "health"),
        ("2026-08-17", "10.00", "Concert at Example Hall", "leisure"),
        ("2026-09-12", "20.00", "Lunch at Example Bistro", "food"),
        ("2026-09-28", "750.00", "Rent for September", "housing"),
        ("2026-09-30", "31.20", "Water bill for September", "utilities"),
        ("2026-10-01", "3.50", "Coffee at Example Cafe", "food"),
        ("2026-10-01", "12.80", "Train ticket to Example City", "transport"),
        ("2026-10-03", "45.10", "Groceries at Example Market", "food"),
        ("2026-10-05", "9.00", "Cinema at Example Plaza", "leisure"),
    ]
    for day, amount, description, category in rows:
        store.add(
            NewExpense(
                amount=Decimal(amount),
                description=description,
                date=date.fromisoformat(day),
                category=category,
                category_source=CategorySource.USER,
            )
        )
    return store
