"""The monthly_report MCP tool, called through the in-memory client.

Every test uses the spec's 16-row dataset and today = 2026-10-15.
"""

from typing import Any

import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent

from expense_tracker.adapters.sqlite_store import SqliteStore


async def call_monthly_report(
    server: MCPServer, arguments: dict[str, Any]
) -> CallToolResult:
    async with Client(server) as client:
        return await client.call_tool("monthly_report", arguments)


def text_of(result: CallToolResult) -> str:
    return "\n".join(
        item.text for item in result.content if isinstance(item, TextContent)
    )


def report_of(result: CallToolResult) -> dict[str, Any]:
    """The structured result of a successful call."""
    assert result.is_error is False, text_of(result)
    assert result.structured_content is not None
    return result.structured_content


@pytest.mark.anyio
@pytest.mark.spec("AC-RPT-01")
async def test_no_arguments_reports_current_month_against_previous(
    report_server: MCPServer, report_dataset: SqliteStore
) -> None:
    result = await call_monthly_report(report_server, {})

    assert report_of(result) == {
        "month": "2026-10",
        "currency": "EUR",
        "total": "70.40",
        "count": 4,
        "categories": [
            {
                "category": "food",
                "total": "48.60",
                "count": 2,
                "percentage": "69.0",
            },
            {
                "category": "transport",
                "total": "12.80",
                "count": 1,
                "percentage": "18.2",
            },
            {
                "category": "leisure",
                "total": "9.00",
                "count": 1,
                "percentage": "12.8",
            },
        ],
        "comparison": {
            "month": "2026-09",
            "total": "801.20",
            "difference": "-730.80",
            "categories": [
                {"category": "food", "total": "20.00", "difference": "+28.60"},
                {
                    "category": "housing",
                    "total": "750.00",
                    "difference": "-750.00",
                },
                {
                    "category": "leisure",
                    "total": "0.00",
                    "difference": "+9.00",
                },
                {
                    "category": "transport",
                    "total": "0.00",
                    "difference": "+12.80",
                },
                {
                    "category": "utilities",
                    "total": "31.20",
                    "difference": "-31.20",
                },
            ],
        },
    }


@pytest.mark.anyio
@pytest.mark.spec("AC-RPT-02")
async def test_explicit_compare_to_a_year_earlier(
    report_server: MCPServer, report_dataset: SqliteStore
) -> None:
    result = await call_monthly_report(
        report_server, {"month": "2026-10", "compare_to": "2025-10"}
    )

    assert report_of(result)["comparison"] == {
        "month": "2025-10",
        "total": "40.00",
        "difference": "+30.40",
        "categories": [
            {"category": "food", "total": "40.00", "difference": "+8.60"},
            {"category": "leisure", "total": "0.00", "difference": "+9.00"},
            {
                "category": "transport",
                "total": "0.00",
                "difference": "+12.80",
            },
        ],
    }


@pytest.mark.anyio
@pytest.mark.spec("AC-RPT-03")
async def test_equal_category_totals_are_ordered_by_name(
    report_server: MCPServer, report_dataset: SqliteStore
) -> None:
    result = await call_monthly_report(report_server, {"month": "2026-08"})

    assert report_of(result)["categories"] == [
        {
            "category": "health",
            "total": "10.00",
            "count": 1,
            "percentage": "50.0",
        },
        {
            "category": "leisure",
            "total": "10.00",
            "count": 1,
            "percentage": "50.0",
        },
    ]


@pytest.mark.anyio
@pytest.mark.spec("AC-RPT-04")
@pytest.mark.parametrize(
    ("month", "expected_categories"),
    [
        (
            "2026-07",
            [
                {
                    "category": "other",
                    "total": "15.00",
                    "count": 1,
                    "percentage": "93.8",
                },
                {
                    "category": "food",
                    "total": "1.00",
                    "count": 1,
                    "percentage": "6.3",
                },
            ],
        ),
        (
            "2026-04",
            [
                {
                    "category": "transport",
                    "total": "3.71",
                    "count": 1,
                    "percentage": "92.8",
                },
                {
                    "category": "food",
                    "total": "0.29",
                    "count": 1,
                    "percentage": "7.3",
                },
            ],
        ),
    ],
    ids=["half-up-adds-to-100.1", "exact-7.25-not-float"],
)
async def test_percentages_round_half_up_with_exact_decimals(
    report_server: MCPServer,
    report_dataset: SqliteStore,
    month: str,
    expected_categories: list[dict[str, Any]],
) -> None:
    result = await call_monthly_report(report_server, {"month": month})

    assert report_of(result)["categories"] == expected_categories


@pytest.mark.anyio
@pytest.mark.spec("AC-RPT-05")
async def test_empty_month_gives_a_zero_report(
    report_server: MCPServer, report_dataset: SqliteStore
) -> None:
    result = await call_monthly_report(report_server, {"month": "2026-06"})

    assert report_of(result) == {
        "month": "2026-06",
        "currency": "EUR",
        "total": "0.00",
        "count": 0,
        "categories": [],
        "comparison": {
            "month": "2026-05",
            "total": "0.00",
            "difference": "0.00",
            "categories": [],
        },
    }


@pytest.mark.anyio
@pytest.mark.spec("AC-RPT-06")
async def test_empty_month_against_month_with_expenses(
    report_server: MCPServer, report_dataset: SqliteStore
) -> None:
    result = await call_monthly_report(
        report_server, {"month": "2026-06", "compare_to": "2026-07"}
    )

    assert report_of(result)["comparison"] == {
        "month": "2026-07",
        "total": "16.00",
        "difference": "-16.00",
        "categories": [
            {"category": "food", "total": "1.00", "difference": "-1.00"},
            {"category": "other", "total": "15.00", "difference": "-15.00"},
        ],
    }


@pytest.mark.anyio
@pytest.mark.spec("AC-RPT-07")
async def test_compare_to_equal_to_month_gives_unsigned_zero_differences(
    report_server: MCPServer, report_dataset: SqliteStore
) -> None:
    result = await call_monthly_report(
        report_server, {"month": "2026-09", "compare_to": "2026-09"}
    )

    assert report_of(result)["comparison"] == {
        "month": "2026-09",
        "total": "801.20",
        "difference": "0.00",
        "categories": [
            {"category": "food", "total": "20.00", "difference": "0.00"},
            {
                "category": "housing",
                "total": "750.00",
                "difference": "0.00",
            },
            {
                "category": "utilities",
                "total": "31.20",
                "difference": "0.00",
            },
        ],
    }


@pytest.mark.anyio
@pytest.mark.spec("AC-RPT-08")
async def test_january_is_compared_with_december_of_previous_year(
    report_server: MCPServer, report_dataset: SqliteStore
) -> None:
    result = await call_monthly_report(report_server, {"month": "2026-01"})

    assert report_of(result)["comparison"] == {
        "month": "2025-12",
        "total": "25.00",
        "difference": "-25.00",
        "categories": [
            {"category": "food", "total": "25.00", "difference": "-25.00"},
        ],
    }


@pytest.mark.anyio
@pytest.mark.spec("AC-RPT-09")
@pytest.mark.parametrize(
    ("arguments", "expected", "expected_comparison"),
    [
        (
            {"month": "2025-12"},
            {"month": "2025-12", "total": "25.00", "count": 1},
            {},
        ),
        (
            {"month": "2024-02"},
            {"month": "2024-02", "total": "8.00", "count": 1},
            {},
        ),
        (
            {"month": "2026-10", "compare_to": "2025-12"},
            {"month": "2026-10"},
            {"month": "2025-12", "total": "25.00"},
        ),
        (
            {"month": "1900-01", "compare_to": "1900-01"},
            {"month": "1900-01", "total": "0.00"},
            {"month": "1900-01", "total": "0.00"},
        ),
    ],
    ids=[
        "31-december-past-year",
        "29-february",
        "compare-to-december",
        "first-month-in-range",
    ],
)
async def test_months_at_calendar_boundaries_include_every_day(
    report_server: MCPServer,
    report_dataset: SqliteStore,
    arguments: dict[str, Any],
    expected: dict[str, Any],
    expected_comparison: dict[str, Any],
) -> None:
    result = await call_monthly_report(report_server, arguments)

    report = report_of(result)
    assert {key: report[key] for key in expected} == expected
    comparison = report["comparison"]
    assert {key: comparison[key] for key in expected_comparison} == (
        expected_comparison
    )


@pytest.mark.anyio
@pytest.mark.spec("AC-RPT-10")
@pytest.mark.parametrize(
    "arguments",
    [{}, {"month": None}, {"month": ""}, {"month": "   "}],
    ids=["missing", "null", "empty", "blank"],
)
async def test_month_not_given_means_current_month(
    report_server: MCPServer,
    report_dataset: SqliteStore,
    arguments: dict[str, Any],
) -> None:
    result = await call_monthly_report(report_server, arguments)

    report = report_of(result)
    assert report["month"] == "2026-10"
    assert report["total"] == "70.40"


@pytest.mark.anyio
@pytest.mark.spec("AC-RPT-11")
@pytest.mark.parametrize(
    "arguments",
    [
        {"month": "2026-10"},
        {"month": "2026-10", "compare_to": None},
        {"month": "2026-10", "compare_to": ""},
        {"month": "2026-10", "compare_to": "   "},
    ],
    ids=["missing", "null", "empty", "blank"],
)
async def test_compare_to_not_given_means_previous_month(
    report_server: MCPServer,
    report_dataset: SqliteStore,
    arguments: dict[str, Any],
) -> None:
    result = await call_monthly_report(report_server, arguments)

    comparison = report_of(result)["comparison"]
    assert comparison["month"] == "2026-09"
    assert comparison["total"] == "801.20"


@pytest.mark.anyio
@pytest.mark.spec("AC-RPT-12")
async def test_month_and_compare_to_are_trimmed(
    report_server: MCPServer, report_dataset: SqliteStore
) -> None:
    result = await call_monthly_report(
        report_server, {"month": " 2026-08 ", "compare_to": " 2026-07 "}
    )

    report = report_of(result)
    assert report["month"] == "2026-08"
    assert report["total"] == "20.00"
    assert report["comparison"]["month"] == "2026-07"
    assert report["comparison"]["total"] == "16.00"


@pytest.mark.anyio
@pytest.mark.spec("AC-RPT-16")
async def test_compare_to_in_the_future_is_a_tool_error(
    report_server: MCPServer, report_dataset: SqliteStore
) -> None:
    result = await call_monthly_report(
        report_server, {"compare_to": "2026-11"}
    )

    assert result.is_error is True
    assert "compare_to cannot be in the future" in text_of(result)
