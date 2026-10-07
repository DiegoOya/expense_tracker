# Plan: add-expense

Spec: [spec.md](spec.md). ADRs: 0001 (functional core, one port),
0002 (SQLite, cents), 0003 (MCP SDK v2, `ToolError`).

## Public interfaces (the contract test-writer codes against)

### `expense_tracker.domain.model`

```python
CATEGORIES: tuple[str, ...]  # the 8 categories, in spec order
CURRENCY = "EUR"
FALLBACK_CATEGORY = "other"
MAX_AMOUNT = Decimal("1000000.00")
MAX_DESCRIPTION_LENGTH = 200


class CategorySource(StrEnum):
    USER = "user"
    AUTO = "auto"


@dataclass(frozen=True)
class NewExpense:  # validated, not stored yet
    amount: Decimal  # always 2 decimal places
    description: str  # trimmed
    date: datetime.date
    category: str
    category_source: CategorySource


@dataclass(frozen=True)
class Expense:  # stored
    id: int
    amount: Decimal  # 2 decimal places, also when read back
    description: str
    date: datetime.date
    category: str
    category_source: CategorySource


class ExpenseValidationError(ValueError):
    """str(error) is exactly the spec message."""
```

### `expense_tracker.domain.categorizer` (the only port)

```python
class Categorizer(Protocol):
    def suggest(self, description: str) -> str | None: ...
```

Contract: returns a category name or `None`; it must not raise. The
domain maps anything outside `CATEGORIES` to `"other"`.

### `expense_tracker.domain.expenses`

```python
def build_expense(
    *,
    amount: str | int | float | bool,
    description: str,
    date: str | None,
    category: str | None,
    today: datetime.date,
    categorizer: Categorizer,
) -> NewExpense: ...
```

Raises `ExpenseValidationError` with the first failure, in the spec's
order. Calls `categorizer.suggest(trimmed_description)` only when the
category is not given. Pure: no clock, no I/O; `today` is passed in.

Amount parsing: `bool` -> invalid; `int` -> exact `Decimal(value)`,
never via `str()` (Python refuses to convert ints over 4300 digits to
text), then the range checks; `float` -> `repr(value)` (shortest
text; exponent -> invalid); `str` -> trimmed. Text must match
`^-?[0-9]+([.,][0-9]+)?$` (ASCII only), then the spec's checks run in
order. Date: trimmed, then `^[0-9]{4}-[0-9]{2}-[0-9]{2}$` plus
`date.fromisoformat` (rejects "20261001" and week dates).

Only the functions and classes listed in this plan are public; helper
functions are `_`-prefixed. Module constants (patterns, messages,
keyword tables) may stay public.

### `expense_tracker.adapters.sqlite_store`

```python
class SqliteStore:
    def __init__(self, path: Path) -> None: ...  # creates the schema
    def add(self, expense: NewExpense) -> Expense: ...
    def get(self, expense_id: int) -> Expense | None: ...
    def list_all(self) -> list[Expense]: ...  # ordered by id
```

Schema `expenses(id INTEGER PRIMARY KEY, amount_cents INTEGER NOT
NULL, description TEXT NOT NULL, date TEXT NOT NULL, category TEXT NOT
NULL, category_source TEXT NOT NULL)`. One connection per call
(MCPServer runs sync tools in worker threads, and `sqlite3`
connections are bound to the thread that created them).

### `expense_tracker.adapters.fake_categorizer`

`FakeCategorizer().suggest(description)`: lower-cases the text and
returns the category of the first keyword found as a whole word (for
example coffee, restaurant -> food; train, bus, taxi -> transport;
rent -> housing; electricity, internet -> utilities; pharmacy,
doctor -> health; cinema, concert -> leisure; clothes, shoes ->
shopping), or `None`. "Gift" maps to nothing.

### `expense_tracker.server`

```python
def build_server(
    store: SqliteStore,
    categorizer: Categorizer,
    today: Callable[[], datetime.date],
) -> MCPServer: ...


def main() -> None: ...  # stdio; see below for the DB path
```

Tool `add_expense(amount: str | int | float | bool, description: str,
date: str | None = None, category: str | None = None) ->
ExpenseOut`, where `ExpenseOut` is a `TypedDict` with the 7 output
keys (`id: int`, the rest `str`). `ExpenseValidationError` is
re-raised as `ToolError(str(error))`. `main()` reads the database
path from `EXPENSE_TRACKER_DB`, default `data/expenses.db` (git-ignored,
same default as `.mcp.json`), creates its parent directory, and uses
`FakeCategorizer` and `date.today`.

Verified on mcp 2.3.0 (scratch probe, 2026-10-06): with this union,
JSON `true` arrives as `bool` and is not coerced to 1, integers stay
`int` (10**30 is exact) and floats stay `float`. `null` and a missing
argument both arrive as `None`.

## Test strategy

| Layer | How | Criteria |
| --- | --- | --- |
| MCP | `Client(build_server(...))`, tmp DB, fixed today | 01, 02, 04 (missing, `null`), 08 (missing, `null`), 14 (JSON 19.99), 16 (JSON 10^5000), 18, 23 |
| Adapter | `SqliteStore(tmp_path / "x.db")`; amounts compared as text, since `Decimal` equality ignores scale | 03, 21 (stored text) |
| Domain | `build_expense(...)`, fixed today, test doubles | all the rest, plus the string values of 04, 08, 14 |

Test doubles live in `tests/`: a categorizer stub returning a fixed
value ("pets", for 09) and a spy recording calls (10, 13). Async tests
use the anyio pytest plugin (`@pytest.mark.anyio`, asyncio backend).

## Files

New: `domain/model.py`, `domain/categorizer.py`,
`domain/expenses.py`, `adapters/sqlite_store.py`,
`adapters/fake_categorizer.py`, `tests/conftest.py`,
`tests/domain/`, `tests/adapters/`, `tests/server/`.
Changed: `server.py` (factory + tool), README (tool list).

## Risks

- **anyio plugin and `--strict-markers`**: check that the `anyio`
  marker is registered; register it in `pyproject.toml` if not.
- **Exact error text through MCP**: the client sees "Error executing
  tool add_expense: <message>", so MCP tests assert "contains".
- **Floats**: `repr` is the only float -> text conversion allowed;
  never `Decimal(float)`.

No new ADR: every decision fits ADRs 0001 to 0003.
