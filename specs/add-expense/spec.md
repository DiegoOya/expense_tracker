---
status: planned
---

# Add expense

## Context

The first tool of the server: an MCP client (e.g. Claude) records one
expense on the user's behalf. Later tools (`list_expenses`,
`monthly_report`) read what this one stores.

## Behaviour

MCP tool `add_expense(amount, description, date?, category?)`.
On success it returns exactly these keys: `id` (integer, 1 for the
first expense, then +1), `amount` (string, 2 decimals), `currency`
(`"EUR"`), `description`, `date` (`YYYY-MM-DD`), `category`,
`category_source` (`"user"` or `"auto"`). On failure it returns a tool
error (`is_error` true) whose text contains the message given below.

Categories: `food`, `transport`, `housing`, `utilities`, `health`,
`leisure`, `shopping`, `other`.

## Input rules

- `amount`: string or JSON number; booleans are invalid. Strings are
  trimmed, then must be ASCII digits with an optional leading `-` and
  an optional `.` or `,` followed by at least one digit ("5." and ".5"
  are invalid). JSON numbers are read by their shortest decimal text
  (19.99 is "19.99"); if that text uses an exponent (1e-05, 1e+20) the
  amount is invalid. Checks, in order: is a decimal number; at most 2
  digits after the separator, even if zeros; greater than 0; at most
  1000000.00.
- `description`: trimmed; 1 to 200 characters after trimming. The
  trimmed text is stored and given to the categorizer.
- `date`, `category`: missing, `null`, `""` or blank mean "not given".
  Date: strict `YYYY-MM-DD`, a real calendar day, not after today.
  Category: trimmed, case-insensitive, must be in the list.
- "Today" is the server's local date from an injectable clock.
- Validation order: amount, description, date, category. Only the
  first failure is reported. A rejected call stores nothing.

Unless stated, criteria assume an empty database, today = 2026-10-06,
the fake categorizer, which maps keywords ("train" -> `transport`) and
suggests nothing for unknown text, and valid values for the inputs a
criterion does not mention. "When added" means when `add_expense` is
called; the plan decides the test layer except where an MCP client is
named. Expected errors are exact messages. When a criterion lists
several example values, every one of them must be tested.

## Acceptance criteria

- **AC-ADD-01** Given amount "12.50", description "Coffee at Example
  Cafe", date "2026-10-01", category "food", when add_expense is called
  through an MCP client, then the structured result is exactly {id: 1,
  amount: "12.50", currency: "EUR", description: "Coffee at Example
  Cafe", date: "2026-10-01", category: "food", category_source:
  "user"}.
- **AC-ADD-02** Given AC-ADD-01 was stored, when the same call is made
  again, then the result has id 2.
- **AC-ADD-03** Given AC-ADD-01 was stored, when the database file is
  opened again, then expense 1 is read back with identical fields.
- **AC-ADD-04** Given the date is missing, `null`, "" or "   ", when
  added, then date is "2026-10-06".
- **AC-ADD-05** Given date "2026-10-06", when added, then it is
  accepted with that date.
- **AC-ADD-06** Given date "2026-10-07", when added, then the error is
  "date cannot be in the future".
- **AC-ADD-07** Given date "01/10/2026", "2026-13-01" or "20261001",
  when added, then the error is "date must be a valid YYYY-MM-DD date".
- **AC-ADD-08** Given the category is missing, `null`, "" or "   " and
  description "Train ticket to Example City", when added, then
  category is "transport" and category_source "auto".
- **AC-ADD-09** Given no category and a categorizer that suggests
  nothing (description "Gift for Example Person") or a value outside
  the list ("pets"), when added, then category is "other" and
  category_source "auto".
- **AC-ADD-10** Given category "food", when added, then the
  categorizer is not called.
- **AC-ADD-11** Given category "  FOOD ", when added, then category is
  "food" and category_source "user".
- **AC-ADD-12** Given category "pets", when added, then the error is
  "category must be one of: food, transport, housing, utilities,
  health, leisure, shopping, other".
- **AC-ADD-13** Given no category and description "  Train ticket  ",
  when added, then the categorizer receives "Train ticket".
- **AC-ADD-14** Given amount 19.99 (JSON number), "7", " 12,50 ",
  "0.01" or "1000000.00", when added, then amount is "19.99", "7.00",
  "12.50", "0.01" or "1000000.00" respectively.
- **AC-ADD-15** Given amount "0" or "-3.00", when added, then the error
  is "amount must be greater than 0".
- **AC-ADD-16** Given amount "1000000.01", when added, then the error
  is "amount must be at most 1000000.00".
- **AC-ADD-17** Given amount "1.234", "12.500", "1,230", "-1.234" or
  "1000000.001", when added, then the error is "amount must have at
  most 2 decimal places".
- **AC-ADD-18** Given amount "abc", "", "NaN", "Infinity", "1e3",
  "1_000", "1.234,50", "5.", ".5", "١٢", JSON `true` or JSON 0.00001,
  when add_expense is called through an MCP client, then the result
  has is_error true and its text contains "amount must be a decimal
  number".
- **AC-ADD-19** Given description "   ", when added, then the error is
  "description must not be empty".
- **AC-ADD-20** Given a description of 201 characters after trimming,
  when added, then the error is "description must be at most 200
  characters".
- **AC-ADD-21** Given a description of 200 characters surrounded by
  spaces, when added, then it is accepted and stored without the
  spaces.
- **AC-ADD-22** Given amount "0" and description "   ", when added,
  then the error is "amount must be greater than 0".
- **AC-ADD-23** Given a rejected call, when a valid expense is added
  next, then the database holds only that expense and its id is 1.

## Out of scope

Editing or deleting expenses; listing and reports (own specs); other
currencies; a real LLM categorizer (own spec); duplicate detection;
user-defined categories; thousands separators; custom messages for
missing required arguments (the SDK's schema validation answers).

## Open questions

None. Resolved with the developer on 2026-10-06: future dates are
rejected, the category list above is kept, the maximum is 1000000.00
and the comma is accepted as decimal separator.
