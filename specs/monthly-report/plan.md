# Plan: monthly-report

Spec: [spec.md](spec.md). ADRs: 0001 (functional core, one port),
0002 (SQLite, cents), 0003 (MCP SDK v2, `ToolError`). Builds on
[add-expense](../add-expense/plan.md) and
[list-expenses](../list-expenses/plan.md).

Approach: the store returns the expenses of each month; aggregation,
ordering, percentages and differences are pure domain functions with
`Decimal`; the server only formats. No SQL aggregation, so every rule
of the spec lives in the functional core.

## Public interfaces (the contract test-writer codes against)

### `expense_tracker.domain.model` (additions)

```python
@dataclass(frozen=True, order=True)
class YearMonth:
    year: int
    month: int  # 1 to 12

    def previous(self) -> YearMonth: ...  # 2026-01 -> 2025-12
    def first_day(self) -> datetime.date: ...
    def last_day(self) -> datetime.date: ...  # calendar.monthrange
    def __str__(self) -> str: ...  # "2026-01"


FIRST_MONTH = YearMonth(1900, 1)


@dataclass(frozen=True)
class ReportRequest:  # validated inputs
    month: YearMonth
    compare_to: YearMonth


@dataclass(frozen=True)
class CategoryShare:
    category: str
    total: Decimal  # 2 decimals
    count: int
    percentage: Decimal  # 1 decimal, half-up


@dataclass(frozen=True)
class CategoryDifference:
    category: str
    total: Decimal  # in the compared month, 0.00 if none
    difference: Decimal  # report month minus compared month


@dataclass(frozen=True)
class Comparison:
    month: YearMonth
    total: Decimal
    difference: Decimal
    categories: tuple[CategoryDifference, ...]  # by category name


@dataclass(frozen=True)
class MonthlyReport:
    month: YearMonth
    total: Decimal
    count: int
    categories: tuple[CategoryShare, ...]  # total desc, then name
    comparison: Comparison
```

`YearMonth` never builds a `date` for an out-of-range year:
`first_day`/`last_day` are only called on validated months (from
1900-01).

### `expense_tracker.domain.parsing` (addition)

```python
def strict_month(text: str) -> YearMonth | None: ...
```

The month of `^[0-9]{4}-(0[1-9]|1[0-2])$` (ASCII digits, so "+2026-10",
"2026 -10" and full-width digits fail), or `None`. "0000-05" parses;
the range check rejects it.

### `expense_tracker.domain.reports` (new)

```python
def build_report_request(
    *, month: str | None, compare_to: str | None, today: datetime.date
) -> ReportRequest: ...


def build_report(
    month: YearMonth,
    expenses: Sequence[Expense],
    compare_to: YearMonth,
    compared_expenses: Sequence[Expense],
) -> MonthlyReport: ...
```

- `build_report_request`: validation in the spec's order (month:
  format, before 1900-01, future; compare_to: the same, or, when not
  given, `month.previous()` unless month is 1900-01). Raises
  `ExpenseValidationError` with the exact spec messages. Pure: `today`
  is passed in.
- `build_report`: totals and counts per category, shares computed as
  `total * 100 / month_total` with `Decimal` and quantized to `0.1`
  with `ROUND_HALF_UP` (never floats), categories ordered by total
  desc then name, comparison categories as the union of both months
  ordered by name. Expenses are assumed to belong to their month
  (the store guarantees it).

### `expense_tracker.adapters.sqlite_store` (addition)

```python
class SqliteStore:
    def between(
        self, first: datetime.date, last: datetime.date
    ) -> list[Expense]: ...  # inclusive, ordered by date then id
```

`WHERE date >= ? AND date <= ?` with bound ISO dates. Called with
`month.first_day()` and `month.last_day()`, so 31 December and 29
February are included.

### `expense_tracker.server` (addition)

Tool `monthly_report(month: str | None = None, compare_to: str | None
= None) -> MonthlyReportOut`, with `TypedDict`s for the report, the
category shares, the comparison and its categories (exact keys of
the spec). `ExpenseValidationError` -> `ToolError(str(error))`.
Registered with `inspect.getdoc` like the other tools; `today` comes
from the injected clock of `build_server`.

Output formatting, in the server: amounts `str(total)`; percentages
`str(percentage)` ("69.0", "100.0"); differences `"0.00"` when equal
to zero (this also covers `Decimal("-0.00")`), else
`format(value, "+.2f")`. Verified 2026-10-11: `format(Decimal("0.00"),
"+.2f")` gives "+0.00" and `str(Decimal("-0.00"))` gives "-0.00", so
the zero check is required.

## Test strategy

The spec's 16-row dataset is a fixture stored through `store.add()`;
a `report_server` fixture builds the server with today = 2026-10-15
(the existing `server` fixture uses 2026-10-06 and stays unchanged).

| Layer | How | Criteria |
| --- | --- | --- |
| MCP | `Client(report_server)` with the dataset; exact structured results | 01 to 12, 16 |
| Domain | `build_report_request(..., today=date(2026, 10, 15))` | 13, 14, 15, 17, 18, 19, 20 |

Report contents are tested through MCP because the spec states them
as exact output strings (signs, decimals).

## Files

New: `domain/reports.py`, tests under `tests/domain/` and
`tests/server/`.
Changed: `domain/model.py`, `domain/parsing.py`,
`adapters/sqlite_store.py`, `server.py`, `tests/conftest.py`
(fixtures), README (tool list).

## Risks

- **Rounding**: floats would round 7.25 down; the April example of
  AC-RPT-04 catches it.
- **Signed zero**: handled by the zero check above; AC-RPT-05 and 07
  catch "+0.00" and "-0.00".
- **Month ends**: computed with `calendar.monthrange`, not a fixed
  day; AC-RPT-08 and 09 catch 31 December and 29 February.
- **Import order in new tests**: as in list-expenses, test files that
  import `domain/reports.py` before it exists will need `ruff --fix
  --select I` once it does (README entries 13 and 18).

No new ADR: aggregation in the domain is ADR 0001's functional core.
