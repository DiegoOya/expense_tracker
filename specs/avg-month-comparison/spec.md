---
status: draft
---

# Average month comparison

## Context

`monthly_report` compares a month with one other month. A single
month is a noisy reference ("is October high compared with a normal
month?"), so this feature adds an optional comparison with the
average of the months before it. It extends the
[monthly-report](../monthly-report/spec.md) spec: its rules and
messages still apply, and its output is unchanged when average_of is
not given.

## Behaviour

MCP tool `monthly_report(month?, compare_to?, average_of?)`.

- `average_of` missing or `null`: the result is exactly the v1 report
  (no `average` key).
- `average_of` X, an integer from 2 to 12 (not a boolean, a string
  or a number written with a fraction such as 3.0): the result also
  has `average` with exactly `months` (X), `first_month` and
  `last_month` ("YYYY-MM", the window), `total`, `difference` and
  `categories`.
- The window is the X months immediately before `month`; `month`
  itself is never in it. Months without expenses count as 0, so the
  average always divides by X.
- `total` is the window's total divided by X; each category's
  `total` is that category's window total divided by X. Each average
  is computed with exact decimal arithmetic and rounded half-up to
  cents on its own, so the category averages may not add up to
  `total`.
- `difference` is the report month's total (or the category's total
  in the report month, "0.00" if none) minus the rounded average,
  signed as in v1 ("+x.xx", "-x.xx", "0.00").
- `categories`: one item per category with expenses in the report
  month or in the window, with exactly `category`, `total` and
  `difference`, ordered by category name.
- `average_of` works with or without `compare_to`; `comparison` is
  unchanged.
- Validation order: month, compare_to (as in v1), then average_of:
  integer, range, then the window must not start before 1900-01.
  Only the first failure is reported.

Unless stated, criteria assume today = 2026-10-15 and the database of
the monthly-report spec. "When reported" means when `monthly_report`
is called; the plan decides the test layer except where an MCP
client is named. Expected errors are exact messages. When a criterion
lists several example values or sub-cases, every one must be tested.

## Acceptance criteria

- **AC-AVG-01** Given month missing and average_of 3, when reported
  through an MCP client, then the result is the one of AC-RPT-01 plus
  average exactly {months: 3, first_month: "2026-07", last_month:
  "2026-09", total: "279.07", difference: "-208.67", categories:
  [{category: "food", total: "7.00", difference: "+41.60"},
  {category: "health", total: "3.33", difference: "-3.33"},
  {category: "housing", total: "250.00", difference: "-250.00"},
  {category: "leisure", total: "3.33", difference: "+5.67"},
  {category: "other", total: "5.00", difference: "-5.00"},
  {category: "transport", total: "0.00", difference: "+12.80"},
  {category: "utilities", total: "10.40", difference: "-10.40"}]}.
- **AC-AVG-02** Given average_of missing or `null` (through an MCP
  client), when reported with no other arguments, then the result is
  exactly the one of AC-RPT-01, without an `average` key.
- **AC-AVG-03** Given month "2026-10" and average_of at the bounds,
  when reported, then average has:
  - average_of 2: first_month "2026-08", last_month "2026-09",
    total "410.60", difference "-340.20".
  - average_of 12: first_month "2025-10", last_month "2026-09",
    total "75.52", difference "-5.12".
- **AC-AVG-04** Given month "2026-05" and average_of 2, when reported,
  then average is exactly {months: 2, first_month: "2026-03",
  last_month: "2026-04", total: "2.00", difference: "-2.00",
  categories: [{category: "food", total: "0.15", difference:
  "-0.15"}, {category: "transport", total: "1.86", difference:
  "-1.86"}]} (0.145 and 1.855 round half-up; floats give "0.14" and
  "1.85").
- **AC-AVG-05** Given month "2026-01" and average_of 3, when reported,
  then average is exactly {months: 3, first_month: "2025-10",
  last_month: "2025-12", total: "21.67", difference: "-21.67",
  categories: [{category: "food", total: "21.67", difference:
  "-21.67"}]} (65.00 / 3: the empty 2025-11 counts as 0; dividing by
  the two months with expenses would give "32.50").
- **AC-AVG-06** Given a report month and window without expenses,
  when reported, then average has total "0.00", difference "0.00"
  and categories []:
  - month "2025-09", average_of 3: first_month "2025-06",
    last_month "2025-08".
  - month "1900-03", average_of 2: first_month "1900-01",
    last_month "1900-02" (the window may start at 1900-01).
  - month "1901-01", average_of 12: first_month "1900-01",
    last_month "1900-12".
- **AC-AVG-07** Given month "2026-10", compare_to "2025-10" and
  average_of 3, when reported, then comparison is the one of
  AC-RPT-02 and average the one of AC-AVG-01.
- **AC-AVG-08** Given average_of "3", "", 3.5, 3.0 or JSON `true`, when
  reported through an MCP client, then the result has is_error true
  and its text contains "average_of must be an integer".
- **AC-AVG-09** Given average_of 0, 1, 13 or -2, when reported, then
  the error is "average_of must be between 2 and 12".
- **AC-AVG-10** Given month "1900-03" with average_of 3, or month
  "1900-12" with average_of 12, when reported, then the error is
  "average_of cannot reach before 1900-01".
- **AC-AVG-11** Given inputs that fail more than one check, when
  reported, then only the first in validation order is reported:
  month "2026-13" with average_of 1 gives "month must be a valid
  YYYY-MM month";
  compare_to "abc" with average_of 1 gives "compare_to must be a
  valid YYYY-MM month"; month "1900-01" without compare_to and with
  average_of 2 gives "compare_to must be given for month 1900-01";
  month "1900-03" with average_of 13 gives "average_of must be
  between 2 and 12"; average_of 13.5 gives "average_of must be an
  integer".
- **AC-AVG-12** Given a database with only 0.29 food on 2026-08-01
  and 1.00 food on 2026-09-01, month "2026-09" and average_of 2, when
  reported, then average total is "0.15" and difference "+0.85", and
  its only category, food, has total "0.15" and difference "+0.85"
  (the difference uses the rounded average: 1.00 - 0.145 rounded
  would give "+0.86").
- **AC-AVG-13** Given month "2026-04" and average_of 3, when
  reported, then average is exactly {months: 3, first_month:
  "2026-01", last_month: "2026-03", total: "0.00", difference:
  "+4.00", categories: [{category: "food", total: "0.00", difference:
  "+0.29"}, {category: "transport", total: "0.00", difference:
  "+3.71"}]} (an empty window; the categories come from the report
  month).

## Out of scope

Windows other than the X months right before `month`; excluding
empty months or months before the first expense; median or other
statistics; percentage change; an average for the compared month;
changing anything of v1 when average_of is not given.

## Open questions

None. Resolved with the developer on 2026-10-21: a parameter of
monthly_report (not a new tool), the X months before month, empty
months count as 0, total and per category, average_of optional from
2 to 12, averages rounded half-up to cents with the difference taken
from the rounded value, and an error for a window before 1900-01.
