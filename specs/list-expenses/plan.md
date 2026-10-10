# Plan: list-expenses

Spec: [spec.md](spec.md). ADRs: 0001 (functional core, one port),
0002 (SQLite), 0003 (MCP SDK v2, `ToolError`). Builds on
[add-expense](../add-expense/plan.md).

## Public interfaces (the contract test-writer codes against)

### `expense_tracker.domain.model` (additions)

```python
DEFAULT_LIMIT = 50
MAX_LIMIT = 200


@dataclass(frozen=True)
class ExpenseFilter:  # validated listing filters
    date_from: datetime.date | None
    date_to: datetime.date | None
    category: str | None  # lower-case, in CATEGORIES
    limit: int  # 1 to MAX_LIMIT


@dataclass(frozen=True)
class ExpensePage:  # one listing result
    expenses: tuple[Expense, ...]  # most recent first
    total_count: int  # matches before `limit`
```

### `expense_tracker.domain.filters` (new)

```python
def build_filter(
    *,
    date_from: str | None,
    date_to: str | None,
    category: str | None,
    limit: int | float | str | bool | None,
) -> ExpenseFilter: ...
```

Pure. Raises `ExpenseValidationError` with the first failure, in the
spec's order: date_from, date_to, date range, category, limit. Limit:
`None` -> `DEFAULT_LIMIT`; `bool` -> "limit must be an integer"
(checked before `int`, since bool is an int); `int` -> range check;
anything else (`str`, `float`) -> "limit must be an integer".

### `expense_tracker.domain.parsing` (new, shared rules)

The rules both tools apply, moved out of `domain/expenses.py` so they
are not duplicated:

```python
UNKNOWN_CATEGORY: str  # "category must be one of: food, ..."


def optional_text(value: str | None) -> str | None: ...
def strict_date(text: str) -> datetime.date | None: ...
def known_category(text: str) -> str | None: ...
```

- `optional_text`: trimmed value, or `None` when missing, `null` or
  blank (today's `_given`).
- `strict_date`: the date for `^[0-9]{4}-[0-9]{2}-[0-9]{2}$` plus
  `date.fromisoformat`, or `None` if invalid. Callers raise their own
  message ("date must ...", "date_from must ...").
- `known_category`: the lower-cased category if it is in
  `CATEGORIES`, else `None`.

`domain/expenses.py` is refactored to use these; its behaviour must
not change (the 23 add-expense criteria stay green, untouched).

### `expense_tracker.adapters.sqlite_store` (addition)

```python
class SqliteStore:
    def search(self, expense_filter: ExpenseFilter) -> ExpensePage: ...
```

One connection, two queries with the same `WHERE` (date bounds,
category): `SELECT ... ORDER BY date DESC, id DESC LIMIT ?` and
`SELECT COUNT(*)`. Bound parameters only, no string formatting of
values. Dates are ISO text, so text comparison is date comparison.
`list_all()` stays as is.

### `expense_tracker.server` (addition)

Tool `list_expenses(date_from: str | None = None, date_to: str |
None = None, category: str | None = None, limit: int | float | str |
bool | None = None) -> ExpenseListOut`, where `ExpenseListOut` is a
`TypedDict` with `expenses: list[ExpenseOut]` and `total_count: int`.
Each expense uses the existing `_to_output`. `ExpenseValidationError`
-> `ToolError(str(error))`. Registered like `add_expense`, with
`inspect.getdoc` for a clean description.

Verified on mcp 2.3.0 (scratch probe, 2026-10-10): with this union,
`limit` arrives unchanged: missing and `null` as `None`, 2 as `int`,
"10" as `str`, 1.5 and 10.0 as `float`, `true` as `bool`.

## Test strategy

The six-row dataset of the spec is a fixture: `store.add()` in the
spec's order (ids 1 to 6).

| Layer | How | Criteria |
| --- | --- | --- |
| MCP | `Client(build_server(...))` with the dataset | 01, 06 (`null`), 08 (201 rows; missing, `null`), 15, 17 |
| Store | `store.search(build_filter(...))` with the dataset | 02, 03, 04, 05, 06 ("", "   "), 07, 09 (201 rows) |
| Domain | `build_filter(...)` | 10, 11, 12, 13, 14, 16 |

Errors in domain tests are exact (`str(error) == message`); through
MCP they are "contained in" the tool error text. Ids are compared as
lists, so order is checked.

## Files

New: `domain/filters.py`, `domain/parsing.py`, tests under
`tests/domain/`, `tests/adapters/`, `tests/server/`.
Changed: `domain/model.py`, `domain/expenses.py` (refactor only),
`adapters/sqlite_store.py`, `server.py`, README (tool list).

## Risks

- **Refactor of add-expense rules**: moving helpers could change a
  message or the trimming; the existing add-expense tests guard it,
  and they must pass without edits.
- **Ordering in SQL**: the date-then-id order lives in the query;
  AC-LST-01 and 03 catch an id-only order because row 6 is out of
  date order.
- **201-row fixtures**: inserted one by one through `store.add()`;
  fast enough with SQLite on `tmp_path`.

No new ADR: `domain/parsing.py` is a helper module of the domain, not
a port or a layer.
