"""The list_expenses MCP tool, called through the in-memory client."""

from typing import Any

import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent

from expense_tracker.adapters.sqlite_store import SqliteStore

ALL_IDS = [5, 4, 3, 2, 6, 1]

CATEGORY_ERROR = (
    "category must be one of: food, transport, housing, utilities, "
    "health, leisure, shopping, other"
)


async def call_list_expenses(
    server: MCPServer, arguments: dict[str, Any]
) -> CallToolResult:
    async with Client(server) as client:
        return await client.call_tool("list_expenses", arguments)


def text_of(result: CallToolResult) -> str:
    return "\n".join(
        item.text for item in result.content if isinstance(item, TextContent)
    )


def ids_of(result: CallToolResult) -> list[int]:
    assert result.structured_content is not None
    return [item["id"] for item in result.structured_content["expenses"]]


@pytest.mark.anyio
@pytest.mark.spec("AC-LST-01")
async def test_no_filters_lists_all_expenses_most_recent_first(
    server: MCPServer, dataset: SqliteStore
) -> None:
    result = await call_list_expenses(server, {})

    assert result.is_error is False
    assert result.structured_content is not None
    assert set(result.structured_content) == {"expenses", "total_count"}
    assert result.structured_content["total_count"] == 6
    assert ids_of(result) == ALL_IDS
    assert result.structured_content["expenses"][0] == {
        "id": 5,
        "amount": "9.00",
        "currency": "EUR",
        "description": "Cinema at Example Plaza",
        "date": "2026-10-05",
        "category": "leisure",
        "category_source": "user",
    }


@pytest.mark.anyio
@pytest.mark.spec("AC-LST-06")
@pytest.mark.parametrize("name", ["date_from", "date_to", "category"], ids=str)
async def test_null_filter_means_not_given(
    server: MCPServer, dataset: SqliteStore, name: str
) -> None:
    result = await call_list_expenses(server, {name: None})

    assert result.is_error is False
    assert result.structured_content is not None
    assert ids_of(result) == ALL_IDS
    assert result.structured_content["total_count"] == 6


@pytest.mark.anyio
@pytest.mark.spec("AC-LST-08")
@pytest.mark.parametrize(
    "limit_argument",
    [{}, {"limit": None}],
    ids=["missing", "null"],
)
async def test_default_limit_is_50_of_201_expenses(
    server: MCPServer,
    many_expenses: SqliteStore,
    limit_argument: dict[str, Any],
) -> None:
    result = await call_list_expenses(server, limit_argument)

    assert result.is_error is False
    assert result.structured_content is not None
    assert len(result.structured_content["expenses"]) == 50
    assert result.structured_content["total_count"] == 201


@pytest.mark.anyio
@pytest.mark.spec("AC-LST-15")
@pytest.mark.parametrize(
    "limit",
    ["10", 1.5, 10.0, True],
    ids=["string", "decimal-number", "decimal-point-integer", "json-true"],
)
async def test_limit_that_is_not_an_integer_is_rejected(
    server: MCPServer, dataset: SqliteStore, limit: Any
) -> None:
    result = await call_list_expenses(server, {"limit": limit})

    assert result.is_error is True
    assert "limit must be an integer" in text_of(result)


@pytest.mark.anyio
@pytest.mark.spec("AC-LST-17")
@pytest.mark.parametrize(
    ("arguments", "expected_error"),
    [
        ({}, None),
        ({"date_from": "2026-10-01", "date_to": "2026-10-03"}, None),
        ({"category": " FOOD "}, None),
        ({"category": "health"}, None),
        ({"limit": 2}, None),
        (
            {"date_from": "01/10/2026"},
            "date_from must be a valid YYYY-MM-DD date",
        ),
        (
            {"date_to": "20261001"},
            "date_to must be a valid YYYY-MM-DD date",
        ),
        (
            {"date_from": "2026-10-05", "date_to": "2026-10-01"},
            "date_from must not be after date_to",
        ),
        ({"category": "pets"}, CATEGORY_ERROR),
        ({"limit": 0}, "limit must be between 1 and 200"),
        ({"limit": 201}, "limit must be between 1 and 200"),
        ({"limit": "10"}, "limit must be an integer"),
        ({"limit": True}, "limit must be an integer"),
        ({"category": "pets", "limit": 0}, CATEGORY_ERROR),
    ],
    ids=[
        "no-filters",
        "date-range",
        "category-padded",
        "category-no-match",
        "limit",
        "bad-date-from",
        "bad-date-to",
        "bad-range",
        "bad-category",
        "limit-zero",
        "limit-too-big",
        "limit-string",
        "limit-true",
        "two-invalid",
    ],
)
async def test_listing_leaves_the_stored_expenses_unchanged(
    server: MCPServer,
    dataset: SqliteStore,
    arguments: dict[str, Any],
    expected_error: str | None,
) -> None:
    before = dataset.list_all()
    assert len(before) == 6

    result = await call_list_expenses(server, arguments)

    if expected_error is None:
        assert result.is_error is False
        assert result.structured_content is not None
        assert set(result.structured_content) == {
            "expenses",
            "total_count",
        }
    else:
        assert result.is_error is True
        assert expected_error in text_of(result)
    assert dataset.list_all() == before
