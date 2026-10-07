"""Shared fixtures and test doubles for the expense tracker tests.

Production modules are imported inside the fixtures so that a missing
implementation only breaks the tests that need it.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from expense_tracker.adapters.sqlite_store import SqliteStore
    from mcp.server.mcpserver import MCPServer

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
    from expense_tracker.adapters.sqlite_store import SqliteStore

    return SqliteStore(db_path)


@pytest.fixture
def server(store: SqliteStore) -> MCPServer:
    from expense_tracker.adapters.fake_categorizer import FakeCategorizer

    from expense_tracker.server import build_server

    return build_server(store, FakeCategorizer(), lambda: TODAY)
