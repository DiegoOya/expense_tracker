# Tasks: avg-month-comparison

Spec: [spec.md](spec.md). Plan: [plan.md](plan.md).
Each task is one commit-sized step. Tick when done.

## Red: tests (test-writer subagent, from spec + plan only)

- [x] T1. AC-AVG-12's two-row database (fixture or test-local setup
  through `store.add()`), served by `report_server`. Covers: none
  (enables AC-AVG-12).
- [x] T2. Domain tests in `tests/domain/test_report_request.py`
  (`build_report_request` with `average_of`). Covers: AC-AVG-09, 10,
  11.
- [x] T3. MCP tests in `tests/server/test_average_comparison.py`.
  Covers: AC-AVG-01 to 08, 12, 13.
- [x] T4. Run pytest: new tests fail only with missing behaviour (or
  an unexpected keyword argument); the existing 315 tests still
  pass. Commit `test(avg-month-comparison)` after the developer
  accepts.

## Green: implementation

- [ ] T5. `domain/model.py`: `MIN_AVERAGE_MONTHS`,
  `MAX_AVERAGE_MONTHS`, `YearMonth.months_before`, `average_of` on
  `ReportRequest`, `AverageComparison`, `average` on `MonthlyReport`.
  Covers: AC-AVG-01, 03 to 07, 12, 13.
- [ ] T6. `domain/reports.py`: `average_of` validation in
  `build_report_request`. Covers: AC-AVG-08 to 11.
- [ ] T7. `domain/reports.py`: `build_average`. Covers: AC-AVG-01, 03
  to 07, 12, 13.
- [ ] T8. `server.py`: `average_of` parameter and docstring, window
  query, `AverageOut` and the `NotRequired` key. Covers: AC-AVG-01 to
  08, 12, 13.
- [ ] T9. Definition of done: ruff, mypy, pytest, check_specs;
  domain purity test still green.

## Review and close

- [ ] T10. `spec-reviewer` feature review; fix findings or explain
  them.
- [ ] T11. Spec `status: implemented`; README tool row and "Next"
  line; README lessons if anything went wrong. Commit
  `feat(avg-month-comparison)` after the developer accepts.
- [ ] T12. Manual check: `monthly_report` with `average_of` called
  from Claude Code via the project's `.mcp.json` server.

Coverage check: every AC-AVG-01 to 13 appears in at least one task.
