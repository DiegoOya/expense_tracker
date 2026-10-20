"""add_expense through an MCP client, with the startup's categorizer.

The categorizer comes from choose_categorizer(os.environ) with the
FakeAnthropicAPI transport, so nothing reaches the network. With
keywords, "Train ticket to Example City" is "transport" and "Gift for
Example Person" matches nothing.
"""

import json
import os
import sys
from typing import Any

import pytest
from conftest import (
    DUMMY_CREDENTIAL,
    TODAY,
    FakeAnthropicAPI,
    answer,
    http_status,
)
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult

from expense_tracker.adapters.sqlite_store import SqliteStore
from expense_tracker.server import build_server
from expense_tracker.startup import choose_categorizer

TRAIN: dict[str, Any] = {
    "amount": "12.80",
    "description": "Train ticket to Example City",
    "date": "2026-10-01",
}

GIFT: dict[str, Any] = {
    "amount": "12.80",
    "description": "Gift for Example Person",
    "date": "2026-10-01",
}

CATEGORIES = [
    "food",
    "transport",
    "housing",
    "utilities",
    "health",
    "leisure",
    "shopping",
    "other",
]


def startup_server(store: SqliteStore, api: FakeAnthropicAPI) -> MCPServer:
    categorizer = choose_categorizer(os.environ, http_client=api.http_client)
    return build_server(store, categorizer, lambda: TODAY)


async def call_add_expense(
    server: MCPServer, arguments: dict[str, Any]
) -> CallToolResult:
    async with Client(server) as client:
        return await client.call_tool("add_expense", arguments)


def output_of(result: CallToolResult) -> dict[str, Any]:
    assert result.is_error is False
    assert result.structured_content is not None
    return result.structured_content


@pytest.fixture
def llm_chosen(
    anthropic_api: FakeAnthropicAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EXPENSE_TRACKER_CATEGORIZER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", DUMMY_CREDENTIAL)


@pytest.mark.anyio
@pytest.mark.spec("AC-LLM-01")
@pytest.mark.parametrize("value", ["anthropic", " Anthropic "])
async def test_llm_answer_becomes_the_auto_category(
    anthropic_api: FakeAnthropicAPI,
    store: SqliteStore,
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("EXPENSE_TRACKER_CATEGORIZER", value)
    monkeypatch.setenv("ANTHROPIC_API_KEY", DUMMY_CREDENTIAL)
    anthropic_api.reply = answer("leisure")
    server = startup_server(store, anthropic_api)

    output = output_of(await call_add_expense(server, TRAIN))

    assert output["category"] == "leisure"
    assert output["category_source"] == "auto"


@pytest.mark.anyio
@pytest.mark.spec("AC-LLM-02")
@pytest.mark.parametrize(
    "sdk_importable", [True, False], ids=["sdk-importable", "sdk-blocked"]
)
@pytest.mark.parametrize(
    "value",
    [None, "", "   ", "keywords", " KEYWORDS "],
    ids=["missing", "empty", "blank", "keywords", "padded-upper-keywords"],
)
async def test_keyword_categorizer_by_default_never_calls_the_api(
    anthropic_api: FakeAnthropicAPI,
    store: SqliteStore,
    monkeypatch: pytest.MonkeyPatch,
    value: str | None,
    sdk_importable: bool,
) -> None:
    if value is not None:
        monkeypatch.setenv("EXPENSE_TRACKER_CATEGORIZER", value)
    if not sdk_importable:
        monkeypatch.setitem(sys.modules, "anthropic", None)
    anthropic_api.reply = answer("leisure")
    server = startup_server(store, anthropic_api)

    output = output_of(await call_add_expense(server, TRAIN))

    assert output["category"] == "transport"
    assert anthropic_api.requests == []


@pytest.mark.anyio
@pytest.mark.spec("AC-LLM-03")
async def test_request_carries_model_description_and_categories_only(
    llm_chosen: None, anthropic_api: FakeAnthropicAPI, store: SqliteStore
) -> None:
    anthropic_api.reply = answer("leisure")
    server = startup_server(store, anthropic_api)

    output_of(await call_add_expense(server, TRAIN))

    assert len(anthropic_api.requests) == 1
    body = anthropic_api.body_text()
    assert json.loads(body)["model"] == "claude-haiku-5-5"
    assert "Train ticket to Example City" in body
    for category in CATEGORIES:
        assert category in body
    assert "12.80" not in body
    assert "2026-10-01" not in body


@pytest.mark.anyio
@pytest.mark.spec("AC-LLM-04")
async def test_given_category_never_calls_the_api(
    llm_chosen: None, anthropic_api: FakeAnthropicAPI, store: SqliteStore
) -> None:
    anthropic_api.reply = answer("leisure")
    server = startup_server(store, anthropic_api)
    arguments = {
        "amount": "12.80",
        "description": "Train ticket to Example City",
        "category": "food",
    }

    output_of(await call_add_expense(server, arguments))

    assert anthropic_api.requests == []


@pytest.mark.anyio
@pytest.mark.spec("AC-LLM-07")
async def test_llm_server_error_still_stores_the_expense_as_other(
    llm_chosen: None, anthropic_api: FakeAnthropicAPI, store: SqliteStore
) -> None:
    anthropic_api.reply = http_status(500)
    server = startup_server(store, anthropic_api)

    result = await call_add_expense(server, GIFT)

    output = output_of(result)
    assert output["category"] == "other"
    assert output["category_source"] == "auto"
