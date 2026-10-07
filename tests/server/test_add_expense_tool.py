"""The add_expense MCP tool, called through the in-memory MCP client."""

from typing import Any

import pytest
from expense_tracker.adapters.sqlite_store import SqliteStore
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent

COFFEE: dict[str, Any] = {
    "amount": "12.50",
    "description": "Coffee at Example Cafe",
    "date": "2026-10-01",
    "category": "food",
}

TRAIN: dict[str, Any] = {
    "amount": "12.50",
    "description": "Train ticket to Example City",
    "date": "2026-10-01",
}


async def call_add_expense(
    server: MCPServer, arguments: dict[str, Any]
) -> CallToolResult:
    async with Client(server) as client:
        return await client.call_tool("add_expense", arguments)


def text_of(result: CallToolResult) -> str:
    return "\n".join(
        item.text for item in result.content if isinstance(item, TextContent)
    )


@pytest.mark.anyio
@pytest.mark.spec("AC-ADD-01")
async def test_first_expense_returns_exact_structured_result(
    server: MCPServer,
) -> None:
    result = await call_add_expense(server, COFFEE)

    assert result.is_error is False
    assert result.structured_content == {
        "id": 1,
        "amount": "12.50",
        "currency": "EUR",
        "description": "Coffee at Example Cafe",
        "date": "2026-10-01",
        "category": "food",
        "category_source": "user",
    }


@pytest.mark.anyio
@pytest.mark.spec("AC-ADD-02")
async def test_second_expense_gets_id_2(server: MCPServer) -> None:
    await call_add_expense(server, COFFEE)

    result = await call_add_expense(server, COFFEE)

    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["id"] == 2


@pytest.mark.anyio
@pytest.mark.spec("AC-ADD-04")
@pytest.mark.parametrize(
    "date_argument",
    [{}, {"date": None}],
    ids=["missing", "null"],
)
async def test_date_not_given_defaults_to_today(
    server: MCPServer, date_argument: dict[str, Any]
) -> None:
    arguments = {k: v for k, v in COFFEE.items() if k != "date"}

    result = await call_add_expense(server, arguments | date_argument)

    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["date"] == "2026-10-06"


@pytest.mark.anyio
@pytest.mark.spec("AC-ADD-08")
@pytest.mark.parametrize(
    "category_argument",
    [{}, {"category": None}],
    ids=["missing", "null"],
)
async def test_category_not_given_is_suggested(
    server: MCPServer, category_argument: dict[str, Any]
) -> None:
    result = await call_add_expense(server, TRAIN | category_argument)

    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["category"] == "transport"
    assert result.structured_content["category_source"] == "auto"


@pytest.mark.anyio
@pytest.mark.spec("AC-ADD-14")
async def test_json_number_amount_uses_its_decimal_text(
    server: MCPServer,
) -> None:
    result = await call_add_expense(server, COFFEE | {"amount": 19.99})

    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["amount"] == "19.99"


@pytest.mark.anyio
@pytest.mark.spec("AC-ADD-18")
@pytest.mark.parametrize(
    "amount",
    [
        "abc",
        "",
        "NaN",
        "Infinity",
        "1e3",
        "1_000",
        "1.234,50",
        "5.",
        ".5",
        "١٢",  # Arabic-Indic digits one and two
        True,
        0.00001,
    ],
    ids=[
        "abc",
        "empty",
        "nan",
        "infinity",
        "exponent-text",
        "underscore",
        "thousands-separator",
        "trailing-dot",
        "leading-dot",
        "arabic-indic-digits",
        "json-true",
        "json-exponent-number",
    ],
)
async def test_amount_that_is_not_a_decimal_number_is_rejected(
    server: MCPServer, amount: Any
) -> None:
    result = await call_add_expense(server, COFFEE | {"amount": amount})

    assert result.is_error is True
    assert "amount must be a decimal number" in text_of(result)


@pytest.mark.anyio
@pytest.mark.spec("AC-ADD-23")
@pytest.mark.parametrize(
    "rejected",
    [
        {"amount": "abc"},
        {"amount": "0"},
        {"description": "   "},
        {"date": "2026-10-07"},
        {"category": "pets"},
    ],
    ids=["not-a-number", "zero", "blank-description", "future", "pets"],
)
async def test_rejected_call_stores_nothing(
    server: MCPServer, store: SqliteStore, rejected: dict[str, Any]
) -> None:
    failed = await call_add_expense(server, COFFEE | rejected)
    assert failed.is_error is True

    result = await call_add_expense(server, COFFEE)

    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["id"] == 1
    stored = store.list_all()
    assert len(stored) == 1
    assert stored[0].id == 1
    assert stored[0].description == "Coffee at Example Cafe"
