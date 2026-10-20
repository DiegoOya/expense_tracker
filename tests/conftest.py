"""Shared fixtures and test doubles for the expense tracker tests.

Production code is imported at the top, like in any module. The one
exception is a red step: a fixture that needs a module the current
feature has not created yet imports it inside the fixture, so the
missing module only breaks the tests that use it. Move that import up
once the module exists.
"""

import json
import os
from collections.abc import Callable, Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import anthropic
import httpx2
import pytest
from mcp.server.mcpserver import MCPServer

from expense_tracker.adapters.fake_categorizer import FakeCategorizer
from expense_tracker.adapters.sqlite_store import SqliteStore
from expense_tracker.domain.model import CategorySource, NewExpense
from expense_tracker.server import build_server

# Fixed "today" for every test (spec: today = 2026-10-06).
TODAY = date(2026, 10, 6)

# Fake Anthropic credential, not key-shaped so secret scanners ignore
# it. Tests choosing the LLM set ANTHROPIC_API_KEY to it.
DUMMY_CREDENTIAL = "dummy-test-credential"

# How the simulated Anthropic API answers one request.
Reply = Callable[[httpx2.Request], httpx2.Response]


def _message_reply(content: list[dict[str, str]], stop_reason: str) -> Reply:
    body: dict[str, Any] = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-5-5",
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "content": content,
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }

    def reply(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=body)

    return reply


def answer_text(text: str) -> Reply:
    """A normal reply whose only text block is ``text``."""
    return _message_reply([{"type": "text", "text": text}], "end_turn")


def answer(category: str) -> Reply:
    """The API "answers X": its text is ``{"category": "X"}``."""
    return answer_text(json.dumps({"category": category}))


def stop(stop_reason: str) -> Reply:
    """A reply that stops with "refusal" or "max_tokens"."""
    if stop_reason == "refusal":
        return _message_reply([], "refusal")
    if stop_reason == "max_tokens":
        truncated = '{"category": "lei'
        return _message_reply(
            [{"type": "text", "text": truncated}], "max_tokens"
        )
    raise ValueError(f"no simulated reply for stop_reason {stop_reason!r}")


def raw_body(body: bytes, content_type: str) -> Reply:
    """A success reply whose raw body is exactly ``body``.

    HTTP 200 with the given bytes and content type, whether or not
    they form a message (AC-LLM-15).
    """

    def reply(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200, content=body, headers={"content-type": content_type}
        )

    return reply


def http_status(code: int) -> Reply:
    """An error reply with HTTP status ``code``."""
    body = {
        "type": "error",
        "error": {"type": "api_error", "message": "simulated"},
    }

    def reply(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(code, json=body)

    return reply


def time_out() -> Reply:
    """The request times out."""

    def reply(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("simulated", request=request)

    return reply


def connection_failure() -> Reply:
    """The connection to the API fails."""

    def reply(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("simulated", request=request)

    return reply


class FakeAnthropicAPI:
    """Simulated Anthropic API behind the SDK's HTTP transport.

    Records every request and its timeout extension; ``reply`` (set
    per test with the helpers above) decides the answer. Nothing
    reaches the network. Until a test sets ``reply``, every request
    gets HTTP 500, so a forgotten reply never looks like a success.
    """

    def __init__(self) -> None:
        self.requests: list[httpx2.Request] = []
        self.timeouts: list[dict[str, Any]] = []
        self.reply: Reply = http_status(500)
        self.http_client = anthropic.DefaultHttpxClient(
            transport=httpx2.MockTransport(self.handle)
        )

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        request.read()
        self.requests.append(request)
        self.timeouts.append(dict(request.extensions["timeout"]))
        return self.reply(request)

    def client(self) -> anthropic.Anthropic:
        return anthropic.Anthropic(
            api_key=DUMMY_CREDENTIAL, http_client=self.http_client
        )

    def body_text(self, index: int = 0) -> str:
        """The body of the recorded request number ``index``."""
        return self.requests[index].content.decode()


@pytest.fixture
def clean_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Hide the developer's Anthropic setup from the test.

    Deletes every ANTHROPIC_* variable and EXPENSE_TRACKER_CATEGORIZER
    and points HOME at an empty directory, so no real key or ant auth
    profile can leak in. Never sets ANTHROPIC_CONFIG_DIR.
    """
    for name in list(os.environ):
        if name.startswith("ANTHROPIC_"):
            monkeypatch.delenv(name)
    monkeypatch.delenv("EXPENSE_TRACKER_CATEGORIZER", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))


@pytest.fixture
def anthropic_api(clean_env: None) -> Iterator[FakeAnthropicAPI]:
    """A simulated Anthropic API, in a clean environment."""
    api = FakeAnthropicAPI()
    yield api
    api.http_client.close()


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
