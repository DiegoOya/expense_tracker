# Plan: llm-categorizer

Spec: [spec.md](spec.md). ADRs: 0001 (functional core, one port for
the LLM). New ADR 0005 (below). Builds on
[add-expense](../add-expense/plan.md): the domain already trims the
description, asks the port only when no category is given, and maps
`None` or unknown names to `other`.

Approach: no domain change. A new adapter implements the existing
`Categorizer` port with the Anthropic SDK and falls back to the
keyword categorizer; a small startup module reads
`EXPENSE_TRACKER_CATEGORIZER`, checks SDK and credentials, and builds
the categorizer that `main()` hands to `build_server`.

Verified on 2026-10-19 against `anthropic` 1.15.0 in a throwaway venv:
`DefaultHttpxClient(transport=httpx2.MockTransport(handler))` reaches
the handler; with `with_options(timeout=10.0, max_retries=0)` the
request's `extensions["timeout"]` is `{"connect": 10.0, "read": 10.0,
"write": 10.0, "pool": 10.0}` and HTTP 500 or a timeout produce one
request; HTTP 429 -> `RateLimitError`, 500 -> `InternalServerError`,
529 -> `OverloadedError`, 408 -> `APIStatusError`, a raised
`httpx2.ReadTimeout` -> `APITimeoutError`, `httpx2.ConnectError` ->
`APIConnectionError`; `Anthropic()` with no credentials builds fine
and has `api_key`, `auth_token` and `credentials` all `None` (also
with `ANTHROPIC_API_KEY=""`); the `ant auth` profile is looked up in
`$HOME/.config/anthropic/` on Linux, and pointing
`ANTHROPIC_CONFIG_DIR` at an empty dir raises `CredentialsError` (an
`AnthropicError`) in the constructor; with `sys.modules["anthropic"]
= None`, `import anthropic` raises `ImportError`.

## Public interfaces (the contract test-writer codes against)

### `expense_tracker.adapters.anthropic_categorizer` (new)

```python
MODEL = "claude-haiku-5-5"
TIMEOUT_SECONDS = 10.0


class AnthropicCategorizer:
    def __init__(
        self, client: anthropic.Anthropic, fallback: Categorizer
    ) -> None: ...

    def suggest(self, description: str) -> str | None: ...
```

- Imports `anthropic` at module level: only importable with the SDK.
- One call per `suggest`:
  `client.with_options(timeout=TIMEOUT_SECONDS, max_retries=0)
  .messages.create(...)` with `model=MODEL`, `max_tokens=64`,
  `thinking={"type": "disabled"}` (accepted by Haiku 5.5 at its
  default effort), a system prompt listing the categories, the
  description as the only user message, and
  `output_config={"format": {"type": "json_schema", "schema": ...}}`
  whose schema is an object with one required `category` string,
  `enum` = `CATEGORIES`, `additionalProperties: false`.
- Result: `stop_reason` "refusal" -> reason `refusal`; "max_tokens"
  -> `max_tokens`; otherwise the first text block is parsed with
  `json.loads`; a dict whose `category` is in `CATEGORIES` is
  returned as is (including "other"); anything else -> `invalid
  answer`. `anthropic.APIError` -> reason `type(error).__name__`.
  AC-LLM-15 (added after the feature review): a 200 reply whose body
  is not a message makes the SDK or the parsing raise
  `JSONDecodeError` (a `ValueError`), `TypeError` or
  `AttributeError` (checked on 2026-10-20 with bodies `not json`,
  `{}` and an HTML page); those three -> `invalid answer`. The
  `JSONDecodeError` comes from inside `messages.create`, so the
  `except` covers the call and the result handling, not only the
  `json.loads` of the answer text.
- On a failure: `print("llm categorizer failed: <reason>; using
  keywords", file=sys.stderr)` (looked up at call time, so `capsys`
  sees it; never stdout, which carries the MCP protocol), then
  `return self.fallback.suggest(description)`. Never raises.

### `expense_tracker.startup` (new)

```python
CATEGORIZER_VARIABLE = "EXPENSE_TRACKER_CATEGORIZER"
UNKNOWN_CATEGORIZER = (
    "EXPENSE_TRACKER_CATEGORIZER must be one of: keywords, anthropic"
)
MISSING_LLM_EXTRA = (
    "EXPENSE_TRACKER_CATEGORIZER=anthropic needs the llm extra "
    "(pip install -e '.[llm]')"
)
MISSING_CREDENTIALS = (
    "EXPENSE_TRACKER_CATEGORIZER=anthropic needs Anthropic credentials "
    "(ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or an ant auth profile)"
)


class ConfigurationError(Exception):  # str(error) is the message
    ...


def choose_categorizer(
    environ: Mapping[str, str], http_client: httpx2.Client | None = None
) -> Categorizer: ...
```

- Value: `environ.get(CATEGORIZER_VARIABLE, "").strip().lower()`.
  `""` or `keywords` -> `FakeCategorizer()`, without importing
  `anthropic`. `anthropic` -> the checks below. Anything else ->
  `ConfigurationError(UNKNOWN_CATEGORIZER)`.
- `anthropic`: `import anthropic` inside the function (the SDK is an
  optional extra; a module-level import would break the default
  install). `ImportError` -> `MISSING_LLM_EXTRA`. Then
  `anthropic.Anthropic(http_client=http_client)`; an
  `AnthropicError` from the constructor (e.g. a selected `ant auth`
  profile that does not exist) or `api_key`, `auth_token` and
  `credentials` all `None` -> `MISSING_CREDENTIALS`. Returns
  `AnthropicCategorizer(client, FakeCategorizer())`.
- The SDK reads the credentials from the process environment, not
  from `environ`; `environ` only carries our own variable. `main()`
  passes `os.environ`; tests use `monkeypatch` on `os.environ` and
  pass `os.environ`.
- `httpx2` is imported under `if TYPE_CHECKING:` for the annotation
  only, for the same optional-dependency reason.

### `expense_tracker.server` (change)

`main()` first calls `choose_categorizer(os.environ)`; on
`ConfigurationError` it writes `str(error)` to stderr and raises
`SystemExit(1)` (no traceback). Only then does it create the database
directory and run the server with the chosen categorizer.
`build_server` is unchanged.

### Packaging and configuration

- `pyproject.toml`: extra `llm = ["anthropic>=1.15,<2"]`; the `dev`
  extra adds `"expense-tracker[llm]"`, so `pip install -e ".[dev]"`
  (setup in AGENTS.md and CI) installs the SDK and every test runs.
  `pip install -e .` stays SDK-free.
- `.mcp.json`: `EXPENSE_TRACKER_CATEGORIZER:
  "${EXPENSE_TRACKER_CATEGORIZER:-keywords}"`.

## Test doubles (tests/conftest.py)

- `FakeAnthropicAPI`: records every `httpx2.Request` and its
  `extensions["timeout"]`; `reply` is set per test. Exposes
  `http_client = anthropic.DefaultHttpxClient(transport=
  httpx2.MockTransport(self.handle))` and `client()` ->
  `anthropic.Anthropic(api_key=DUMMY_CREDENTIAL,
  http_client=self.http_client)`.
- Replies (helpers): answer X -> HTTP 200 with
  `{"id": "msg_test", "type": "message", "role": "assistant",
  "model": "claude-haiku-5-5", "stop_reason": "end_turn",
  "stop_sequence": null, "content": [{"type": "text", "text":
  "<text>"}], "usage": {"input_tokens": 1, "output_tokens": 1}}`
  where text is `{"category": "X"}` (or any raw text for the
  not-JSON cases); a stop reason -> the same with that
  `stop_reason` (`"refusal"`: empty content; `"max_tokens"`:
  truncated text `{"category": "lei`); HTTP status N -> `{"type":
  "error", "error": {"type": "api_error", "message": "simulated"}}`;
  timeout -> `raise httpx2.ReadTimeout("simulated", request=r)`;
  connection failure -> `raise httpx2.ConnectError("simulated",
  request=r)`; a 200 reply with a raw body (AC-LLM-15) ->
  `httpx2.Response(200, content=<bytes>, headers={"content-type":
  <type>})`.
- `DUMMY_CREDENTIAL = "dummy-test-credential"` (not key-shaped, so
  gitleaks stays quiet).
- `clean_env` fixture: deletes every `ANTHROPIC_*` variable and
  `EXPENSE_TRACKER_CATEGORIZER`, and sets `HOME` to `tmp_path`, so no
  real key or `ant auth` profile on the developer's machine can leak
  in. Never sets `ANTHROPIC_CONFIG_DIR` (it raises, see above).
  Tests that choose the LLM set `ANTHROPIC_API_KEY` to the dummy.
- SDK not importable: `monkeypatch.setitem(sys.modules, "anthropic",
  None)`.

## Test strategy

| Layer | How | Criteria |
| --- | --- | --- |
| Adapter | `AnthropicCategorizer(api.client(), FakeCategorizer()).suggest(...)`; `api.requests`; `capsys` | 05, 06, 08, 09, 10, 11 |
| Startup | `main()` under `clean_env` with `pytest.raises(SystemExit)`; exit code and `capsys` stderr | 12, 13, 14 |
| MCP | `Client(build_server(store, choose_categorizer(os.environ, http_client=api.http_client), lambda: TODAY))` under `clean_env` | 01, 02, 03, 04, 07 |

AC-LLM-02 runs once with the SDK importable and once with it blocked.
AC-LLM-12 to 14 go through `main()` because the exit status and the
"only the message" stderr are part of the criteria; `main()` fails
before touching the database or stdio.

## Files

New: `adapters/anthropic_categorizer.py`, `startup.py`,
`docs/adr/0005-opt-in-llm-categorizer.md`, tests
`tests/adapters/test_anthropic_categorizer.py`,
`tests/test_startup.py`, `tests/server/test_llm_categorizer_tool.py`.
Changed: `server.py` (`main`), `pyproject.toml`, `.mcp.json`,
`tests/conftest.py`, README (setup, privacy note, lessons). AGENTS.md
stays as is: its setup command already installs the `dev` extra.

## Risks

- **Real key in tests**: a developer with `ANTHROPIC_API_KEY` or an
  `ant auth` profile could make tests hit the real API. `clean_env`
  plus the injected transport make that impossible: no test builds a
  client without `FakeAnthropicAPI`'s transport.
- **SDK drift**: request/response shapes come from the SDK, not
  hand-written HTTP; the fake's reply shape was checked with 1.15.0.
  The version range is `<2`.
- **SDK logging**: the `anthropic` logger has no handler, so its
  warnings would reach stderr through Python's last-resort handler
  and break AC-LLM-10/11's "exactly one line". `clean_env` avoids the
  conditions that trigger them (credential shadowing).
- **`.mcp.json` and the key**: whether Claude Code passes its own
  environment (`ANTHROPIC_API_KEY`) to a stdio server is not checked
  yet; the manual check (last task) confirms it before the README
  says how to enable the LLM from Claude Code.
- **Self-referencing extra** (`expense-tracker[llm]` inside `dev`):
  supported by pip 21.2+; the venv has 26.2.1.
- **Import order**: new test files import modules that do not exist
  yet; after green, `ruff --fix --select I` regroups them (README
  entries 13 and 18).

ADR 0005: descriptions leave the machine only by explicit opt-in;
keywords are the fallback; one attempt with a 10 s timeout keeps
`add_expense` responsive.
