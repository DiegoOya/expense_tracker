# 2. SQLite storage, integer cents, single currency

- Status: accepted
- Date: 2026-10-05

## Context

A personal tracker needs durable local storage with zero setup, and
money must not suffer float rounding.

## Decision

- SQLite through the standard `sqlite3` module; the file path comes
  from `EXPENSE_TRACKER_DB` (default `data/expenses.db`, git-ignored).
- Amounts are `decimal.Decimal` at the edges (MCP input/output, domain)
  and `INTEGER` cents in the database.
- One currency (EUR), as a constant. No multi-currency support.
- No ORM and no migrations tool; the schema is created on startup.

## Consequences

- Tests use a temporary database file per test.
- Changing the schema later means adding a small migration step by
  hand, which is acceptable at this size.
