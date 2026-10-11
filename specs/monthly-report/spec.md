---
status: draft
---

# Monthly report

## Context

An MCP client (e.g. Claude) needs a summary of one month of spending
to answer "how much did I spend in October, and on what?" and "is it
more than last month?". The per-expense detail belongs to
`list_expenses`; this tool returns aggregates only.

## Behaviour

MCP tool `monthly_report(month?, compare_to?)`. On success it returns
exactly these keys:

- `month` ("YYYY-MM"), `currency` ("EUR"), `total` (string, 2
  decimals) and `count` (integer): the report month.
- `categories`: one item per category with expenses in the month,
  with exactly `category`, `total`, `count` and `percentage` (the
  category's share of the month total, string with 1 decimal).
  Ordered by total, highest first; equal totals by category name.
- `comparison`: exactly `month` (the compared month), `total` (its
  total), `difference` (report total minus compared total) and
  `categories`: one item per category with expenses in either month,
  with exactly `category`, `total` (in the compared month, "0.00" if
  none) and `difference` (report month minus compared month), ordered
  by category name.

Amounts and differences are strings with 2 decimals. Amounts have no
sign. Differences always show their sign: "+" when positive, "-" when
negative, and no sign for "0.00". On failure it
returns a tool error (`is_error` true) whose text contains the
message given below.

## Input rules

- `month`, `compare_to`: trimmed; missing, `null`, `""` or blank mean
  "not given". Format: strict `YYYY-MM`, ASCII digits only, a month
  from 01 to 12. Range: from 1900-01 to the current month (a past
  year accepts any month number, e.g. "2025-12"). Expenses dated
  before 1900 can be stored by add_expense but not reported.
- `month` not given: the current month. `compare_to` not given: the
  month before `month` (January -> December of the year before).
  `compare_to` may equal `month`. Month "1900-01" has no month before
  it in range, so it needs an explicit `compare_to`.
- A month includes every day of it, from the 1st to its last day
  (28, 29, 30 or 31).
- Percentages are computed with exact decimal arithmetic (never
  binary floats) and rounded half-up to one decimal, each on its
  own, so they may not add up to 100.0.
- "Today" is the server's local date from an injectable clock.
- Validation order: month (format, before 1900-01, future), then
  compare_to (format, before 1900-01, future; when not given, whether
  month has a month before it). Only the first failure is reported.

Unless stated, criteria assume today = 2026-10-15 and this database
(storage order does not matter):

| date | amount | description | category |
| --- | --- | --- | --- |
| 2024-02-29 | 8.00 | Taxi to Example Airport | transport |
| 2025-10-10 | 40.00 | Dinner at Example Restaurant | food |
| 2025-12-31 | 25.00 | New Year dinner at Example Bistro | food |
| 2026-04-10 | 0.29 | Chewing gum at Example Kiosk | food |
| 2026-04-11 | 3.71 | Bus ticket to Example Town | transport |
| 2026-07-05 | 1.00 | Coffee at Example Kiosk | food |
| 2026-07-20 | 15.00 | Gift for Example Person | other |
| 2026-08-03 | 10.00 | Pharmacy at Example Street | health |
| 2026-08-17 | 10.00 | Concert at Example Hall | leisure |
| 2026-09-12 | 20.00 | Lunch at Example Bistro | food |
| 2026-09-28 | 750.00 | Rent for September | housing |
| 2026-09-30 | 31.20 | Water bill for September | utilities |
| 2026-10-01 | 3.50 | Coffee at Example Cafe | food |
| 2026-10-01 | 12.80 | Train ticket to Example City | transport |
| 2026-10-03 | 45.10 | Groceries at Example Market | food |
| 2026-10-05 | 9.00 | Cinema at Example Plaza | leisure |

"When reported" means when `monthly_report` is called; the plan
decides the test layer except where an MCP client is named. Expected
errors are exact messages. When a criterion lists several example
values or sub-cases, every one of them must be tested.

## Acceptance criteria

- **AC-RPT-01** Given no arguments, when reported through an MCP
  client, then the structured result is exactly {month: "2026-10",
  currency: "EUR", total: "70.40", count: 4, categories: [{category:
  "food", total: "48.60", count: 2, percentage: "69.0"}, {category:
  "transport", total: "12.80", count: 1, percentage: "18.2"},
  {category: "leisure", total: "9.00", count: 1, percentage: "12.8"}],
  comparison: {month: "2026-09", total: "801.20", difference:
  "-730.80", categories: [{category: "food", total: "20.00",
  difference: "+28.60"}, {category: "housing", total: "750.00",
  difference: "-750.00"}, {category: "leisure", total: "0.00",
  difference: "+9.00"}, {category: "transport", total: "0.00",
  difference: "+12.80"}, {category: "utilities", total: "31.20",
  difference: "-31.20"}]}}.
- **AC-RPT-02** Given month "2026-10" and compare_to "2025-10", when
  reported, then comparison is exactly {month: "2025-10", total:
  "40.00", difference: "+30.40", categories: [{category: "food", total:
  "40.00", difference: "+8.60"}, {category: "leisure", total: "0.00",
  difference: "+9.00"}, {category: "transport", total: "0.00",
  difference: "+12.80"}]}.
- **AC-RPT-03** Given month "2026-08", when reported, then categories
  is exactly [{category: "health", total: "10.00", count: 1,
  percentage: "50.0"}, {category: "leisure", total: "10.00", count: 1,
  percentage: "50.0"}] (equal totals ordered by name).
- **AC-RPT-04** Given a month whose shares need rounding, when
  reported, then categories is exactly:
  - month "2026-07": [{category: "other", total: "15.00", count: 1,
    percentage: "93.8"}, {category: "food", total: "1.00", count: 1,
    percentage: "6.3"}] (6.25 rounds half-up; the shares add up to
    100.1).
  - month "2026-04": [{category: "transport", total: "3.71", count: 1,
    percentage: "92.8"}, {category: "food", total: "0.29", count: 1,
    percentage: "7.3"}] (exactly 7.25; float arithmetic would give
    7.2499... and "7.2").
- **AC-RPT-05** Given month "2026-06", when reported, then the result
  is exactly {month: "2026-06", currency: "EUR", total: "0.00", count:
  0, categories: [], comparison: {month: "2026-05", total: "0.00",
  difference: "0.00", categories: []}}.
- **AC-RPT-06** Given month "2026-06" and compare_to "2026-07", when
  reported, then comparison is exactly {month: "2026-07", total:
  "16.00", difference: "-16.00", categories: [{category: "food", total:
  "1.00", difference: "-1.00"}, {category: "other", total: "15.00",
  difference: "-15.00"}]}.
- **AC-RPT-07** Given month "2026-09" and compare_to "2026-09", when
  reported, then comparison is exactly {month: "2026-09", total:
  "801.20", difference: "0.00", categories: [{category: "food", total:
  "20.00", difference: "0.00"}, {category: "housing", total:
  "750.00", difference: "0.00"}, {category: "utilities", total:
  "31.20", difference: "0.00"}]}.
- **AC-RPT-08** Given month "2026-01", when reported, then comparison
  is exactly {month: "2025-12", total: "25.00", difference: "-25.00",
  categories: [{category: "food", total: "25.00", difference:
  "-25.00"}]}.
- **AC-RPT-09** Given a month at a calendar boundary, when reported,
  then:
  - month "2025-12": total "25.00" and count 1 (31 December counts,
    and a past year accepts a month number after the current one).
  - month "2024-02": total "8.00" and count 1 (29 February counts).
  - month "2026-10" with compare_to "2025-12": comparison total
    "25.00".
  - month "1900-01" with compare_to "1900-01": total "0.00" and
    comparison total "0.00" (the first month in range is accepted).
- **AC-RPT-10** Given month missing, `null`, "" or "   " (through an
  MCP client), when reported, then month is "2026-10" and total is
  "70.40".
- **AC-RPT-11** Given compare_to missing, `null`, "" or "   " with
  month "2026-10" (through an MCP client), when reported, then
  comparison month is "2026-09" and its total is "801.20".
- **AC-RPT-12** Given month " 2026-08 " and compare_to " 2026-07 ",
  when reported, then month is "2026-08", total "20.00", and
  comparison month "2026-07" with total "16.00".
- **AC-RPT-13** Given month "2026-13", "2026-00", "2026-1", "10-2026",
  "2026/10", "2026-10-01", "abc", "+2026-10", "2026 -10" or
  "２０２６-10" (full-width digits), when reported, then the error is
  "month must be a valid YYYY-MM month".
- **AC-RPT-14** Given month "2026-11" or "2027-01", when reported,
  then the error is "month cannot be in the future".
- **AC-RPT-15** Given compare_to "2026-13", "2026-1" or "abc", when
  reported, then the error is "compare_to must be a valid YYYY-MM
  month".
- **AC-RPT-16** Given compare_to "2026-11" through an MCP client, when
  reported, then the result has is_error true and its text contains
  "compare_to cannot be in the future".
- **AC-RPT-17** Given month "1900-01" and no compare_to, when
  reported, then the error is "compare_to must be given for month
  1900-01".
- **AC-RPT-18** Given two invalid inputs, when reported, then only the
  first in validation order is reported: month "2026-13" with
  compare_to "abc" gives "month must be a valid YYYY-MM month"; month
  "1899-12" with compare_to "abc" gives "month cannot be before
  1900-01"; month "2026-11" with compare_to "abc" gives "month cannot
  be in the future".
- **AC-RPT-19** Given month "1899-12" or "0000-05", when reported,
  then the error is "month cannot be before 1900-01".
- **AC-RPT-20** Given compare_to "1899-12", when reported, then the
  error is "compare_to cannot be before 1900-01".

## Out of scope

Comparison with the average of the last X months (a later spec);
percentage change between months; several months or custom date
ranges in one report; filtering by category; per-expense detail
(`list_expenses`); messages for non-string `month` or `compare_to`
values (the SDK's schema validation answers).

## Open questions

None. Resolved with the developer on 2026-10-11: report contents,
optional month defaulting to the current one, compare_to defaulting
to the previous month and comparing total and categories, zero report
for an empty month, error for a future month, breakdown order and
percentage rounding. Resolved on 2026-10-11 after the spec review:
differences always show their sign, compare_to may equal month, a
future compare_to is an error, and months start at 1900-01.
