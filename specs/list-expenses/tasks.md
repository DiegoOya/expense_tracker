# Tasks: list-expenses

Spec: [spec.md](spec.md). Plan: [plan.md](plan.md).
Each task is one commit-sized step. Tick when done.

## Red: tests (test-writer subagent, from spec + plan only)

- [x] T1. Test fixtures: the spec's six-row dataset stored in order
  (ids 1 to 6) and a 201-row store; reuse the existing `store`,
  `server` and anyio fixtures. Covers: none (enables all).
- [x] T2. Domain tests in `tests/domain/test_build_filter.py`.
  Covers: AC-LST-10, 11, 12, 13, 14, 16.
- [x] T3. Store tests in `tests/adapters/test_search.py`.
  Covers: AC-LST-02, 03, 04, 05, 06 ("", "   "), 07, 09.
- [x] T4. MCP tests in `tests/server/test_list_expenses_tool.py`.
  Covers: AC-LST-01, 06 (`null`), 08, 15, 17.
- [x] T5. Run pytest: new tests fail only with import errors or
  missing behaviour; the existing 138 tests still pass. Commit
  `test(list-expenses)` after the developer accepts.

## Green: implementation

- [x] T6. `domain/parsing.py`: move `optional_text`, `strict_date`,
  `known_category` and `UNKNOWN_CATEGORY` out of `domain/expenses.py`
  and use them there. Covers: shared rules for AC-LST-03, 04, 06, 10,
  11, 13; add-expense tests must stay green untouched.
- [x] T7. `domain/model.py` (`ExpenseFilter`, `ExpensePage`,
  `DEFAULT_LIMIT`, `MAX_LIMIT`) and `domain/filters.py`
  (`build_filter`). Covers: AC-LST-06, 10 to 14, 16.
- [x] T8. `SqliteStore.search`. Covers: AC-LST-01 to 05, 07, 08, 09.
- [x] T9. `server.py`: `list_expenses` tool, `ExpenseListOut`,
  `ToolError` mapping. Covers: AC-LST-01, 06, 08, 15, 17.
- [x] T10. Definition of done: ruff, mypy, pytest, check_specs;
  domain purity test still green.

## Review and close

- [x] T11. `spec-reviewer` feature review; fix findings or explain
  them.
- [x] T12. Spec `status: implemented`; README tool list; README
  lessons if anything went wrong. Commit `feat(list-expenses)` after
  the developer accepts.
- [x] T13. Manual check: `list_expenses` called from Claude Code via
  the project's `.mcp.json` server.

Coverage check: every AC-LST-01 to 17 appears in at least one task.
