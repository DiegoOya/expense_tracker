"""The average_of option of monthly_report, through the MCP client.

Unless stated, tests use the 16-row dataset of the monthly-report spec
and today = 2026-10-15. The expected values of AC-RPT-01 and AC-RPT-02
are copied from specs/monthly-report/spec.md because
test_monthly_report_tool.py does not expose them.
"""

from typing import Any

import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent

from expense_tracker.adapters.sqlite_store import SqliteStore

# AC-RPT-01: the result of monthly_report with no arguments.
RPT_01_RESULT: dict[str, Any] = {
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
            {"category": "leisure", "total": "0.00", "difference": "+9.00"},
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

# AC-RPT-02: the comparison of 2026-10 with 2025-10.
RPT_02_COMPARISON: dict[str, Any] = {
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

# AC-AVG-01: the average of the 3 months before 2026-10.
AVERAGE_OCT_3: dict[str, Any] = {
    "months": 3,
    "first_month": "2026-07",
    "last_month": "2026-09",
    "total": "279.07",
    "difference": "-208.67",
    "categories": [
        {"category": "food", "total": "7.00", "difference": "+41.60"},
        {"category": "health", "total": "3.33", "difference": "-3.33"},
        {
            "category": "housing",
            "total": "250.00",
            "difference": "-250.00",
        },
        {"category": "leisure", "total": "3.33", "difference": "+5.67"},
        {"category": "other", "total": "5.00", "difference": "-5.00"},
        {
            "category": "transport",
            "total": "0.00",
            "difference": "+12.80",
        },
        {
            "category": "utilities",
            "total": "10.40",
            "difference": "-10.40",
        },
    ],
}

NOT_INTEGER_ERROR = "average_of must be an integer"


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


def average_of_report(result: CallToolResult) -> dict[str, Any]:
    """The `average` object of a successful call."""
    report = report_of(result)
    assert "average" in report
    average: dict[str, Any] = report["average"]
    return average


@pytest.mark.anyio
@pytest.mark.spec("AC-AVG-01")
async def test_average_of_3_adds_the_average_of_the_three_months_before(
    report_server: MCPServer, report_dataset: SqliteStore
) -> None:
    result = await call_monthly_report(report_server, {"average_of": 3})

    assert report_of(result) == {**RPT_01_RESULT, "average": AVERAGE_OCT_3}


@pytest.mark.anyio
@pytest.mark.spec("AC-AVG-02")
@pytest.mark.parametrize(
    "arguments",
    [{}, {"average_of": None}],
    ids=["missing", "null"],
)
async def test_average_of_not_given_leaves_the_report_unchanged(
    report_server: MCPServer,
    report_dataset: SqliteStore,
    arguments: dict[str, Any],
) -> None:
    result = await call_monthly_report(report_server, arguments)

    report = report_of(result)
    assert report == RPT_01_RESULT
    assert "average" not in report


@pytest.mark.anyio
@pytest.mark.spec("AC-AVG-03")
@pytest.mark.parametrize(
    ("average_of", "expected"),
    [
        (
            2,
            {
                "months": 2,
                "first_month": "2026-08",
                "last_month": "2026-09",
                "total": "410.60",
                "difference": "-340.20",
            },
        ),
        (
            12,
            {
                "months": 12,
                "first_month": "2025-10",
                "last_month": "2026-09",
                "total": "75.52",
                "difference": "-5.12",
            },
        ),
    ],
    ids=["lower-bound-2", "upper-bound-12"],
)
async def test_average_of_at_the_bounds(
    report_server: MCPServer,
    report_dataset: SqliteStore,
    average_of: int,
    expected: dict[str, Any],
) -> None:
    result = await call_monthly_report(
        report_server, {"month": "2026-10", "average_of": average_of}
    )

    average = average_of_report(result)
    assert {key: average[key] for key in expected} == expected


@pytest.mark.anyio
@pytest.mark.spec("AC-AVG-04")
async def test_averages_round_half_up_with_exact_decimals(
    report_server: MCPServer, report_dataset: SqliteStore
) -> None:
    result = await call_monthly_report(
        report_server, {"month": "2026-05", "average_of": 2}
    )

    assert average_of_report(result) == {
        "months": 2,
        "first_month": "2026-03",
        "last_month": "2026-04",
        "total": "2.00",
        "difference": "-2.00",
        "categories": [
            {"category": "food", "total": "0.15", "difference": "-0.15"},
            {
                "category": "transport",
                "total": "1.86",
                "difference": "-1.86",
            },
        ],
    }


@pytest.mark.anyio
@pytest.mark.spec("AC-AVG-05")
async def test_window_crossing_a_year_counts_empty_months_as_zero(
    report_server: MCPServer, report_dataset: SqliteStore
) -> None:
    result = await call_monthly_report(
        report_server, {"month": "2026-01", "average_of": 3}
    )

    assert average_of_report(result) == {
        "months": 3,
        "first_month": "2025-10",
        "last_month": "2025-12",
        "total": "21.67",
        "difference": "-21.67",
        "categories": [
            {"category": "food", "total": "21.67", "difference": "-21.67"},
        ],
    }


@pytest.mark.anyio
@pytest.mark.spec("AC-AVG-06")
@pytest.mark.parametrize(
    ("month", "average_of", "first_month", "last_month"),
    [
        ("2025-09", 3, "2025-06", "2025-08"),
        ("1900-03", 2, "1900-01", "1900-02"),
        ("1901-01", 12, "1900-01", "1900-12"),
    ],
    ids=["no-expenses", "window-starts-at-1900-01", "year-1900-in-full"],
)
async def test_month_and_window_without_expenses_give_a_zero_average(
    report_server: MCPServer,
    report_dataset: SqliteStore,
    month: str,
    average_of: int,
    first_month: str,
    last_month: str,
) -> None:
    result = await call_monthly_report(
        report_server, {"month": month, "average_of": average_of}
    )

    assert average_of_report(result) == {
        "months": average_of,
        "first_month": first_month,
        "last_month": last_month,
        "total": "0.00",
        "difference": "0.00",
        "categories": [],
    }


@pytest.mark.anyio
@pytest.mark.spec("AC-AVG-07")
async def test_average_of_works_together_with_compare_to(
    report_server: MCPServer, report_dataset: SqliteStore
) -> None:
    result = await call_monthly_report(
        report_server,
        {"month": "2026-10", "compare_to": "2025-10", "average_of": 3},
    )

    report = report_of(result)
    assert report["comparison"] == RPT_02_COMPARISON
    assert report["average"] == AVERAGE_OCT_3


@pytest.mark.anyio
@pytest.mark.spec("AC-AVG-08")
@pytest.mark.parametrize(
    "average_of",
    ["3", "", 3.5, 3.0, True],
    ids=["string", "empty-string", "fraction", "float-3.0", "boolean"],
)
async def test_average_of_that_is_not_an_integer_is_a_tool_error(
    report_server: MCPServer,
    report_dataset: SqliteStore,
    average_of: int | float | str | bool,
) -> None:
    result = await call_monthly_report(
        report_server, {"average_of": average_of}
    )

    assert result.is_error is True
    assert NOT_INTEGER_ERROR in text_of(result)


@pytest.mark.anyio
@pytest.mark.spec("AC-AVG-12")
async def test_difference_is_taken_from_the_rounded_average(
    report_server: MCPServer, rounding_dataset: SqliteStore
) -> None:
    result = await call_monthly_report(
        report_server, {"month": "2026-09", "average_of": 2}
    )

    assert average_of_report(result) == {
        "months": 2,
        "first_month": "2026-07",
        "last_month": "2026-08",
        "total": "0.15",
        "difference": "+0.85",
        "categories": [
            {"category": "food", "total": "0.15", "difference": "+0.85"},
        ],
    }


@pytest.mark.anyio
@pytest.mark.spec("AC-AVG-13")
async def test_empty_window_takes_its_categories_from_the_report_month(
    report_server: MCPServer, report_dataset: SqliteStore
) -> None:
    result = await call_monthly_report(
        report_server, {"month": "2026-04", "average_of": 3}
    )

    assert average_of_report(result) == {
        "months": 3,
        "first_month": "2026-01",
        "last_month": "2026-03",
        "total": "0.00",
        "difference": "+4.00",
        "categories": [
            {"category": "food", "total": "0.00", "difference": "+0.29"},
            {
                "category": "transport",
                "total": "0.00",
                "difference": "+3.71",
            },
        ],
    }
