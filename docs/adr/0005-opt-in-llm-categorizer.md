# 5. Opt-in LLM categorizer with a keyword fallback

- Status: accepted
- Date: 2026-10-20

## Context

The keyword categorizer only knows a few words, so most expenses end
up as `other`. Claude classifies descriptions far better, but calling
it sends user data to a third party, needs credentials and can be
slow or fail. The project must still run and pass CI without a key
(ADR 1 already reserved the `Categorizer` port for this).

## Decision

- `AnthropicCategorizer` (adapters) implements the port with the
  Anthropic SDK and model `claude-haiku-5-5`, chosen by the developer
  for a short, high-volume classification.
- **Opt-in**: only `EXPENSE_TRACKER_CATEGORIZER=anthropic` enables
  it. Having credentials is not enough, because sending descriptions
  out of the machine must be an explicit choice. Only the description
  and the category list are sent, never amount or date.
- **Fail fast at startup, fail soft per request.** An unknown value,
  a missing `llm` extra or no credentials stop the server. Any
  failure of one request (timeout, HTTP error, refusal, answer outside
  the list) is one stderr line, and the keyword categorizer decides.
  `add_expense` never fails because of the LLM.
- **One attempt, 10-second timeout**: `add_expense` stays responsive;
  the SDK's default retries are turned off.
- The answer is constrained with structured outputs (a JSON schema
  whose `category` is an enum of the categories); the adapter still
  validates it.
- The SDK is the optional `llm` extra, imported only when chosen.
  `dev` includes it so every test runs in CI, against a simulated
  HTTP transport, never the real API.

## Consequences

- `category_source` stays `"auto"`: clients cannot tell an LLM answer
  from a keyword one (a later spec could add that).
- A bad key is only noticed per request, as stderr lines and keyword
  categories; startup checks presence, not validity.
- Accuracy is not measured; an eval would be its own feature.
