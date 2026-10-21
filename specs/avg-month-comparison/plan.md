# Plan: avg-month-comparison

Spec: [spec.md](spec.md). ADRs: 0001 (functional core, one port),
0003 (MCP SDK v2, `ToolError`). Builds on
[monthly-report](../monthly-report/plan.md): same request/report
split, same Decimal arithmetic, same signed formatting.

Approach: one more optional input in `build_report_request`, one new
pure function `build_average`, one store query for the whole window,
and an optional `average` key in the tool output. Nothing in the v1
path changes when `average_of` is not given.

Verified on 2026-10-21 with mcp 2.3.0: a `TypedDict` output with a
`NotRequired` key leaves it out of the output schema's `required`,
and a result without the key reaches the client without it (needed
for AC-AVG-02). A union parameter `int | float | str | bool | None`
keeps the JSON type, as `list_expenses`' `limit` already relies on.

## Public interfaces (the contract test-writer codes against)

### `expense_tracker.domain.model` (additions)

```python
MIN_AVERAGE_MONTHS = 2
MAX_AVERAGE_MONTHS = 12


class YearMonth:  # existing
    # 2026-01 .months_before(3) -> 2025-10; months_before(1) is
    # previous(); may return a month before FIRST_MONTH (checked by
    # the caller).
    def months_before(self, count: int) -> YearMonth: ...


@dataclass(frozen=True)
class ReportRequest:  # existing, one field added with a default
    month: YearMonth
    compare_to: YearMonth
    average_of: int | None = None


@dataclass(frozen=True)
class AverageComparison:
    months: int  # X
    first_month: YearMonth
    last_month: YearMonth  # the month before the report month
    total: Decimal  # window total / X, half-up to cents
    difference: Decimal  # report month total minus `total`
    # `total` of each item is that category's rounded average:
    categories: tuple[CategoryDifference, ...]  # by category name


@dataclass(frozen=True)
class MonthlyReport:  # existing, one field added with a default
    ...
    average: AverageComparison | None = None
```

### `expense_tracker.domain.reports` (changes)

```python
AVERAGE_OF_NOT_INTEGER = "average_of must be an integer"
AVERAGE_OF_OUT_OF_RANGE = "average_of must be between 2 and 12"
AVERAGE_BEFORE_FIRST_MONTH = "average_of cannot reach before 1900-01"


def build_report_request(
    *,
    month: str | None,
    compare_to: str | None,
    average_of: int | float | str | bool | None = None,
    today: datetime.date,
) -> ReportRequest: ...


def build_average(
    month_expenses: Sequence[Expense],
    window_expenses: Sequence[Expense],
    *,
    month: YearMonth,
    months: int,
) -> AverageComparison: ...
```

- `build_report_request`: the v1 checks unchanged and first; then
  `average_of`: `None` -> not given; a `bool`, or anything that is
  not an `int` (`"3"`, `""`, 3.5, 3.0) -> `AVERAGE_OF_NOT_INTEGER`;
  outside 2..12 -> `AVERAGE_OF_OUT_OF_RANGE`;
  `month.months_before(x) < FIRST_MONTH` ->
  `AVERAGE_BEFORE_FIRST_MONTH`. The messages are constants built
  from the model constants. Existing callers without `average_of`
  keep working (default `None`).
- `build_average`: window is `month.months_before(months)` to
  `month.previous()`; per category and overall, `window total /
  months` quantized to `0.01` with `ROUND_HALF_UP` (Decimal, never
  floats); each difference is the report month's value (`0.00` if
  none) minus the rounded average; categories are the union of the
  report month's and the window's, sorted by name. The window
  expenses are assumed to fall inside the window (the store
  guarantees it).

### `expense_tracker.adapters.sqlite_store`

No change: the server reads the window with one call,
`store.between(first_month.first_day(), last_month.last_day())`.

### `expense_tracker.server` (changes)

- `monthly_report(month: str | None = None, compare_to: str | None =
  None, average_of: int | float | str | bool | None = None)`; the
  docstring gains one line for `average_of`. `ExpenseValidationError`
  -> `ToolError(str(error))` as in v1.
- When `request.average_of` is set: `build_average(...)` and
  `dataclasses.replace(report, average=...)`.
- Output: new `AverageOut` TypedDict (`months: int`, `first_month`,
  `last_month`, `total`, `difference`: `str`, `categories:
  list[CategoryDifferenceOut]`); `MonthlyReportOut` gains `average:
  NotRequired[AverageOut]`, filled only when `report.average` is not
  `None`. Amounts with `str(...)`, differences with the existing
  `_signed`.

## Test strategy

Fixtures already exist: `report_server` (today 2026-10-15) and
`report_dataset` (the 16 rows of the monthly-report spec). AC-AVG-12
needs its own two-row database: a fixture or test-local setup that
stores 0.29 food on 2026-08-01 and 1.00 food on 2026-09-01 through
`store.add()`, served by `report_server`.

| Layer | How | Criteria |
| --- | --- | --- |
| MCP | `Client(report_server)` with the dataset; exact structured results | 01, 02, 03, 04, 05, 06, 07, 08, 12, 13 |
| Domain | `build_report_request(..., today=date(2026, 10, 15))` | 09, 10, 11 |

AC-AVG-02 compares with the exact AC-RPT-01 dict and asserts the
`average` key is absent. AC-AVG-08 goes through the client because
the JSON type of the value is the point.

## Files

New: tests under `tests/domain/` and `tests/server/`.
Changed: `domain/model.py`, `domain/reports.py`, `server.py`,
`tests/conftest.py` (only if a fixture is added), README (tool row).

## Risks

- **Rounding**: floats would give "0.14"/"1.85" in AC-AVG-04 and
  Decimal's default half-even "0.14"; both fail.
- **Rounded difference**: AC-AVG-12 fails if the difference is
  rounded from the exact average.
- **v1 unchanged**: the new fields have defaults, so existing tests
  and callers keep working; AC-AVG-02 and the v1 suite guard it.
- **Import order** in new tests (README entries 13 and 18).

No new ADR: an extension of the monthly report inside ADR 0001.
