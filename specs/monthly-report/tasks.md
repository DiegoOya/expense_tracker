# Tasks: monthly-report

Spec: [spec.md](spec.md). Plan: [plan.md](plan.md).
Each task is one commit-sized step. Tick when done.

## Red: tests (test-writer subagent, from spec + plan only)

- [x] T1. Test fixtures: the spec's 16-row dataset stored through
  `store.add()` and a `report_server` fixture with today =
  2026-10-15; the existing `server` fixture stays unchanged. Covers:
  none (enables all).
- [x] T2. Domain tests in `tests/domain/test_report_request.py`
  (`build_report_request`). Covers: AC-RPT-13, 14, 15, 17, 18, 19,
  20.
- [x] T3. MCP tests in `tests/server/test_monthly_report_tool.py`.
  Covers: AC-RPT-01 to 12, 16.
- [x] T4. Run pytest: new tests fail only with import errors or
  missing behaviour; the existing 197 tests still pass. Commit
  `test(monthly-report)` after the developer accepts.

## Green: implementation

- [x] T5. `YearMonth`, `FIRST_MONTH` and `ReportRequest` in
  `domain/model.py`; `strict_month` in `domain/parsing.py`;
  `build_report_request` in `domain/reports.py`. Covers: AC-RPT-08,
  10 to 15, 17 to 20.
- [x] T6. Report types and `build_report` in `domain/reports.py`.
  Covers: AC-RPT-01 to 09.
- [x] T7. `SqliteStore.between`. Covers: AC-RPT-01, 02, 05 to 09.
- [x] T8. `server.py`: `monthly_report` tool, output `TypedDict`s,
  signed-difference formatting, `ToolError` mapping. Covers:
  AC-RPT-01 to 12, 16.
- [x] T9. Definition of done: ruff, mypy, pytest, check_specs;
  domain purity test still green.

## Review and close

- [x] T10. `spec-reviewer` feature review; fix findings or explain
  them.
- [x] T11. Spec `status: implemented`; README tool list; README
  lessons if anything went wrong. Commit `feat(monthly-report)` after
  the developer accepts.
- [ ] T12. Manual check: `monthly_report` called from Claude Code via
  the project's `.mcp.json` server.

Coverage check: every AC-RPT-01 to 20 appears in at least one task.
