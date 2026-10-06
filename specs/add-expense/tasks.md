# Tasks: add-expense

Spec: [spec.md](spec.md). Plan: [plan.md](plan.md).
Each task is one commit-sized step. Tick when done.

## Red: tests (test-writer subagent, from spec + plan only)

- [ ] T1. Test infrastructure: `tests/conftest.py` with `TODAY =
  date(2026, 10, 6)`, temporary database, `client` fixture over
  `build_server(...)`, categorizer stub and spy; anyio backend
  fixture. Covers: none (enables all).
- [ ] T2. Domain tests in `tests/domain/test_build_expense.py`.
  Covers: AC-ADD-04 (string values), 05, 06, 07, 08 (string values),
  09, 10, 11, 12, 13, 14 (string values), 15, 16, 17, 19, 20, 21, 22.
- [ ] T3. Adapter tests in `tests/adapters/test_sqlite_store.py`.
  Covers: AC-ADD-03, 21 (stored text).
- [ ] T4. MCP tests in `tests/server/test_add_expense_tool.py`.
  Covers: AC-ADD-01, 02, 04 (missing, `null`), 08 (missing, `null`),
  14 (JSON 19.99), 18, 23.
- [ ] T5. Run pytest: the new tests fail only with import errors or
  missing behaviour, never with errors in the tests themselves.
  Commit `test(add-expense)`.

## Green: implementation

- [ ] T6. `domain/model.py` and `domain/categorizer.py` (types,
  constants, error, port). Covers: structure for all ACs.
- [ ] T7. `domain/expenses.py`: `build_expense` with amount, description,
  date and category rules in spec order. Covers: AC-ADD-04 to 22
  (domain part).
- [ ] T8. `adapters/fake_categorizer.py`. Covers: AC-ADD-08, 09.
- [ ] T9. `adapters/sqlite_store.py`. Covers: AC-ADD-03, 21, 23.
- [ ] T10. `server.py`: `build_server`, `add_expense` tool,
  `ToolError` mapping, `main()` wiring. Covers: AC-ADD-01, 02, 04,
  08, 14, 18, 23.
- [ ] T11. Definition of done: ruff, mypy, pytest, check_specs;
  domain purity test still green.

## Review and close

- [ ] T12. `spec-reviewer` feature review; fix findings or explain
  them.
- [ ] T13. Spec `status: implemented`; README tool list; README
  lessons if anything went wrong. Commit `feat(add-expense)`.
- [ ] T14. Manual check: `add_expense` called from Claude Code via
  the project's `.mcp.json` server.

Coverage check: every AC-ADD-01 to 23 appears in at least one task.
