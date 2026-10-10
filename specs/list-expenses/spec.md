---
status: planned
---

# List expenses

## Context

An MCP client (e.g. Claude) needs the detail of stored expenses to
answer questions such as "what did I spend on food this month?".
Totals and aggregates belong to `monthly_report`, not to this tool.

## Behaviour

MCP tool `list_expenses(date_from?, date_to?, category?, limit?)`.
On success it returns exactly two keys: `expenses`, a list of
expenses with exactly the 7 keys returned by `add_expense`, and
`total_count`, the number of stored expenses that match the filters,
regardless of `limit`. Expenses are ordered by date, most recent
first, and by id descending for the same date. No match is not an
error: it returns an empty list and `total_count` 0. On failure it
returns a tool error (`is_error` true) whose text contains the message
given below. Listing never changes stored data.

## Input rules

- `date_from`, `date_to`, `category`: trimmed; missing, `null`, `""`
  or blank mean "not given". Dates: strict `YYYY-MM-DD`, a real
  calendar day, inclusive bounds. A bound may be after today (e.g.
  `date_to` = end of the current month): stored expenses are never in
  the future (add-expense rejects them), so this only leaves the range
  open and needs no clock. Category: case-insensitive, must be in the
  category list of add-expense.
- `limit`: a JSON integer from 1 to 200; missing or `null` means 50.
  Strings, booleans and JSON numbers with a decimal point (even 10.0)
  are invalid.
- Validation order: date_from, date_to, date range, category, limit.
  Only the first failure is reported.

Unless stated, criteria assume this database, stored in this order
(ids 1 to 6; id 6 is stored last but dated earlier, so date order and
id order differ), and valid values for the inputs a criterion does
not mention:

| id | date | amount | description | category |
| --- | --- | --- | --- | --- |
| 1 | 2026-09-28 | 750.00 | Rent for September | housing |
| 2 | 2026-10-01 | 3.50 | Coffee at Example Cafe | food |
| 3 | 2026-10-01 | 12.80 | Train ticket to Example City | transport |
| 4 | 2026-10-03 | 45.10 | Groceries at Example Market | food |
| 5 | 2026-10-05 | 9.00 | Cinema at Example Plaza | leisure |
| 6 | 2026-09-30 | 31.20 | Water bill for September | utilities |

All six have category_source "user". Unfiltered order: 5, 4, 3, 2,
6, 1. "When listed" means when
`list_expenses` is called; the plan decides the test layer except
where an MCP client is named. Expected errors are exact messages.
When a criterion lists several example values, every one of them
must be tested.

## Acceptance criteria

- **AC-LST-01** Given no filters, when listed through an MCP client,
  then the structured result has `total_count` 6, the expenses have
  ids 5, 4, 3, 2, 6, 1 in that order, and the first one is exactly {id:
  5, amount: "9.00", currency: "EUR", description: "Cinema at Example
  Plaza", date: "2026-10-05", category: "leisure", category_source:
  "user"}.
- **AC-LST-02** Given an empty database, or the filter category
  "health", when listed, then the result is {expenses: [],
  total_count: 0}.
- **AC-LST-03** Given a date filter, when listed, then only expenses
  inside the inclusive bounds are returned, in this order:
  - date_from "2026-10-01" or " 2026-10-01 ": ids 5, 4, 3, 2;
    total_count 4.
  - date_to "2026-10-01": ids 3, 2, 6, 1; total_count 4.
  - date_from "2026-10-01" with date_to "2026-10-03": ids 4, 3, 2;
    total_count 3.
  - date_from "2026-10-01" with date_to "2026-10-01": ids 3, 2;
    total_count 2.
  - date_to "2026-12-31": ids 5, 4, 3, 2, 6, 1; total_count 6.
- **AC-LST-04** Given category "food" or " FOOD ", when listed, then
  the ids are 4, 2 and total_count is 2.
- **AC-LST-05** Given date_from "2026-10-02" and category "food", when
  listed, then the ids are 4 and total_count is 1.
- **AC-LST-06** Given one filter (date_from, date_to or category) set
  to `null`, "" or "   " and the others not given (9 calls), when
  listed, then the ids are 5, 4, 3, 2, 6, 1 and total_count is 6.
- **AC-LST-07** Given limit 2, when listed, then the ids are 5, 4 and
  total_count is 6.
- **AC-LST-08** Given 201 stored expenses (instead of the table) and
  limit missing or `null`
  (through an MCP client), when listed, then 50 expenses are returned
  and total_count is 201.
- **AC-LST-09** Given 201 stored expenses and limit 1 or 200, when
  listed, then 1 or 200 expenses are returned respectively and
  total_count is 201.
- **AC-LST-10** Given date_from "01/10/2026", "2026-13-01" or
  "20261001", when listed, then the error is "date_from must be a
  valid YYYY-MM-DD date".
- **AC-LST-11** Given date_to "01/10/2026", "2026-13-01" or
  "20261001", when listed, then the error is "date_to must be a valid
  YYYY-MM-DD date".
- **AC-LST-12** Given date_from "2026-10-05" and date_to "2026-10-01",
  when listed, then the error is "date_from must not be after
  date_to".
- **AC-LST-13** Given category "pets", when listed, then the error is
  "category must be one of: food, transport, housing, utilities,
  health, leisure, shopping, other".
- **AC-LST-14** Given limit 0, -1 or 201, when listed, then the error
  is "limit must be between 1 and 200".
- **AC-LST-15** Given limit "10", 1.5, 10.0 or JSON `true`, when listed
  through an MCP client, then the result has is_error true and its
  text contains "limit must be an integer".
- **AC-LST-16** Given two invalid inputs, when listed, then only the
  first in validation order is reported: date_from "x" with date_to
  "y" gives the date_from error; date_to "y" with category "pets"
  gives the date_to error; date_from "2026-10-05", date_to
  "2026-10-01" and category "pets" give the date range error;
  category "pets" with limit 0 gives the category error.
- **AC-LST-17** Given any call of AC-LST-01 to 16, when the database
  is read afterwards, then it holds the same expenses as before.

## Out of scope

Text search in descriptions; amount filters; pagination (offset);
several categories at once; other sort orders; totals and aggregates
(monthly_report).

## Open questions

None. Resolved with the developer on 2026-10-10: filters are only the
date range and category; limit 50 by default, 200 at most, no
pagination; most recent first; `limit` accepts only JSON integers;
filter bounds may be after today.
