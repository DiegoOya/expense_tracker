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

- [x] T5. `domain/model.py`: `MIN_AVERAGE_MONTHS`,
  `MAX_AVERAGE_MONTHS`, `YearMonth.months_before`, `average_of` on
  `ReportRequest`, `AverageComparison`, `average` on `MonthlyReport`.
  Covers: AC-AVG-01, 03 to 07, 12, 13.
- [x] T6. `domain/reports.py`: `average_of` validation in
  `build_report_request`. Covers: AC-AVG-08 to 11.
- [x] T7. `domain/reports.py`: `build_average`. Covers: AC-AVG-01, 03
  to 07, 12, 13.
- [x] T8. `server.py`: `average_of` parameter and docstring, window
  query, `AverageOut` and the `NotRequired` key. Covers: AC-AVG-01 to
  08, 12, 13.
- [x] T9. Definition of done: ruff, mypy, pytest, check_specs;
  domain purity test still green.

## Review and close

- [x] T10. `spec-reviewer` feature review; fix findings or explain
  them.
- [x] T11. Spec `status: implemented`; README tool row and "Next"
  line; README lessons if anything went wrong. Commit
  `feat(avg-month-comparison)` after the developer accepts.
- [x] T12. Manual check: `monthly_report` with `average_of` called
  from Claude Code via the project's `.mcp.json` server.
  Done 2026-10-26 on the local (git-ignored) database. With only
  October stored, `average_of` 3 gave an empty window (average
  "0.00", differences equal to the month's totals). After adding nine
  fictitious expenses from July to September with explicit
  categories, the average was "65.15" (195.45 / 3), difference
  "+92.55", food "19.17" / "-14.67", transport "15.17" / "+108.63",
  leisure "10.00" / "+14.90", utilities "20.82" / "-20.82", other
  "0.00" / "+4.50"; the category averages add up to 65.16, not
  65.15, as the spec says. All values match a hand calculation.

Coverage check: every AC-AVG-01 to 13 appears in at least one task.
