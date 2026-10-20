---
status: implemented
---

# LLM categorizer

## Context

When `add_expense` gets no category, the keyword categorizer only
knows a few words ("train", "coffee"), so most descriptions end up as
`other`. This feature adds an opt-in categorizer backed by Claude
(Anthropic API) behind the existing `Categorizer` port. The keyword
categorizer stays the default, so the project runs and passes CI
without any key.

## Behaviour

- `EXPENSE_TRACKER_CATEGORIZER` chooses the categorizer when the
  server starts. Trimmed and case-insensitive: missing, blank or
  `keywords` means the keyword categorizer; `anthropic` the LLM one.
- Startup checks, in order: the value is known; for `anthropic`, the
  Anthropic SDK can be imported (the `llm` extra), then credentials
  exist (an API key or auth token other than the empty string, or an
  `ant auth` profile). Only the first failure is reported: the server
  exits with status 1 and only the message (no traceback) on stderr.
  The keyword categorizer needs neither the SDK nor credentials.
- The LLM categorizer sends only the description it receives and the
  category list, with model `claude-haiku-5-5`, one attempt (no
  retries of any kind) and a 10-second timeout. The answer is the
  JSON object `{"category": "<name>"}`, and the name must equal one of
  the 8 categories exactly; `other` is a valid answer.
- If the LLM fails (timeout, network error, any HTTP error, refusal,
  stop at max_tokens, unparseable answer, name outside the list, a
  success reply whose body is not a message), the
  keyword categorizer decides, then the usual fallback `other`
  applies. `add_expense` never fails because of the LLM. Each failure
  writes one stderr line `llm categorizer failed: <reason>; using
  keywords`: `<reason>` is the SDK exception class name, `refusal`,
  `max_tokens` or `invalid answer`, never the description or a
  credential.
- `category_source` stays `"auto"` whoever suggested the category.

Criteria assume a simulated Anthropic API: an HTTP transport given to
the SDK client that records each request (body and timeout) and
replies as the criterion says, or raises a timeout or connection
error. "Answers X" means a normal reply whose text is
`{"category": "X"}`; "replies with HTTP status N" means an error
reply; "a success reply whose raw body is B" means HTTP 200 with
exactly the bytes B and the stated content type. No network or real
key: tests remove the developer's `ANTHROPIC_*` variables and use an
empty `ant auth` config location; where the LLM categorizer is
chosen they set ANTHROPIC_API_KEY to a dummy value. The dev setup
installs the SDK. "Startup" is the server's startup routine run with
the given environment; criteria through an MCP client use the
categorizer it chose. With keywords, "Train ticket to Example City"
is `transport` and "Gift for Example Person" matches nothing.
Messages are exact. Every listed example value or sub-case must be
tested.

## Acceptance criteria

- **AC-LLM-01** Given EXPENSE_TRACKER_CATEGORIZER "anthropic" or
  " Anthropic " and the API answering "leisure", when add_expense is
  called through an MCP client with description "Train ticket to
  Example City" and no category, then category is "leisure" and
  category_source "auto".
- **AC-LLM-02** Given EXPENSE_TRACKER_CATEGORIZER missing, "", "   ",
  "keywords" or " KEYWORDS ", no Anthropic credentials, and the
  Anthropic SDK importable or impossible to import, when the same
  call is made, then category is "transport" and no request
  reaches the API.
- **AC-LLM-03** Given the LLM categorizer, when add_expense is called
  through an MCP client with amount "12.80", date "2026-10-01",
  description "Train ticket to Example City" and no category, then
  exactly one request reaches the API, and its body names model
  "claude-haiku-5-5", contains the description and the 8 category
  names, and contains neither "12.80" nor "2026-10-01".
- **AC-LLM-04** Given the LLM categorizer, when add_expense is called
  with amount "12.80", description "Train ticket to Example City" and
  category "food", then no request reaches the API.
- **AC-LLM-05** Given the API answers "food", "transport", "housing",
  "utilities", "health", "leisure", "shopping" or "other", when the
  LLM categorizer suggests for "Train ticket to Example City", then
  the suggestion is that answer ("other" too, not "transport").
- **AC-LLM-06** Given the API times out, the connection fails, it
  replies with HTTP status 400, 401, 403, 404, 408, 429, 500 or 529,
  it stops with stop_reason "refusal" or "max_tokens", it answers
  "pets" or "Food", or its text is not JSON or is JSON without
  "category", when the LLM categorizer suggests for "Train ticket to
  Example City", then the suggestion is "transport".
- **AC-LLM-07** Given the LLM categorizer and the API replying with
  HTTP status 500, when add_expense is called through an MCP client
  with description "Gift for Example Person" and no category, then
  the call succeeds with category "other" and category_source "auto".
- **AC-LLM-08** Given the API times out, the connection fails, or it
  replies with HTTP status 408, 429, 500 or 529, when the LLM
  categorizer suggests for "Train ticket to Example City", then
  exactly one request reaches the API.
- **AC-LLM-09** Given the LLM categorizer, when it suggests for "Train
  ticket to Example City", then every part of the recorded request's
  timeout (connect, read, write, pool) is 10 seconds.
- **AC-LLM-10** Given a failing API, when the LLM categorizer
  suggests for "Train ticket to Example City", then stderr is exactly
  one line naming the reason, without the description or the dummy
  credential:
  - HTTP status 429: "llm categorizer failed: RateLimitError; using
    keywords".
  - timeout: "llm categorizer failed: APITimeoutError; using
    keywords".
  - connection failure: "llm categorizer failed: APIConnectionError;
    using keywords".
  - stop_reason "refusal": "llm categorizer failed: refusal; using
    keywords".
  - stop_reason "max_tokens": "llm categorizer failed: max_tokens;
    using keywords".
  - answer "pets", text that is not JSON, JSON without "category", or
    an HTTP 200 body that is not a message (the five bodies of
    AC-LLM-15): "llm categorizer failed: invalid answer; using
    keywords".
- **AC-LLM-11** Given the API answers "leisure", when the LLM
  categorizer suggests for "Train ticket to Example City", then
  nothing is written to stderr.
- **AC-LLM-12** Given EXPENSE_TRACKER_CATEGORIZER "openai", "llm" or
  "anthropic-api", when the server starts, then it exits with status
  1 and stderr is "EXPENSE_TRACKER_CATEGORIZER must be one of:
  keywords, anthropic".
- **AC-LLM-13** Given EXPENSE_TRACKER_CATEGORIZER "anthropic", the
  Anthropic SDK impossible to import and no credentials, when the
  server starts, then it exits with status 1 and stderr is
  "EXPENSE_TRACKER_CATEGORIZER=anthropic needs the llm extra (pip
  install -e '.[llm]')".
- **AC-LLM-14** Given EXPENSE_TRACKER_CATEGORIZER "anthropic" and no
  credentials (no `ANTHROPIC_*` variables, or ANTHROPIC_API_KEY "",
  with an empty `ant auth` config location), when the server starts,
  then it exits with status 1 and stderr is
  "EXPENSE_TRACKER_CATEGORIZER=anthropic needs Anthropic credentials
  (ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or an ant auth profile)".
- **AC-LLM-15** Given the API sends a success reply whose raw body is
  not a message: the text `not json` (content type
  application/json), the JSON object `{}` (content type
  application/json), the page `<html>proxy</html>` (content type
  text/html), or a normal reply whose text block has `"text": 5` or
  `"text": null` instead of a string, when the LLM categorizer
  suggests for "Train ticket to Example City", then the suggestion is
  "transport".

## Out of scope

Choosing the model or timeout by configuration; other LLM providers;
telling `"llm"` from `"keyword"` in `category_source`; recategorizing
stored expenses; caching answers; measuring the LLM's accuracy (an
eval); checking at startup that the credentials are valid (a bad key
is a per-request failure, AC-LLM-06). Tests and CI never call the
real API; the developer checks it by hand once.

## Open questions

None. Resolved with the developer on 2026-10-19: model Claude Haiku
5.5, opt-in through EXPENSE_TRACKER_CATEGORIZER, keywords then
`other` when the LLM fails, `category_source` unchanged, startup
errors for a bad configuration, 10 s and no retries, "other" from the
LLM is kept, and one stderr line per failure. Added on 2026-10-20,
after the feature review found that a malformed success reply made
`add_expense` fail: AC-LLM-15 and its AC-LLM-10 sub-case. AC-LLM-15
has the same outcome as AC-LLM-06 but keeps its own ID, at the
developer's request, to record the amendment. The non-string `text`
examples were added the same day after the final review found they
still made `add_expense` fail.
