# Tasks: llm-categorizer

Spec: [spec.md](spec.md). Plan: [plan.md](plan.md).
Each task is one commit-sized step. Tick when done.

## Red: tests (test-writer subagent, from spec + plan only)

- [x] T1. `pyproject.toml`: `llm` extra and `dev` pulling it in;
  reinstall the venv, so the tests can import `anthropic` and
  `httpx2`. Covers: none (enables all).
- [x] T2. Test doubles in `tests/conftest.py`: `FakeAnthropicAPI`
  with its reply helpers, `DUMMY_CREDENTIAL` and the `clean_env`
  fixture. Covers: none (enables all).
- [x] T3. Adapter tests in
  `tests/adapters/test_anthropic_categorizer.py`. Covers: AC-LLM-05,
  06, 08, 09, 10, 11.
- [x] T4. Startup tests in `tests/test_startup.py` (through
  `main()`). Covers: AC-LLM-12, 13, 14.
- [x] T5. MCP tests in `tests/server/test_llm_categorizer_tool.py`.
  Covers: AC-LLM-01, 02, 03, 04, 07.
- [x] T6. Run pytest: new tests fail only with import errors or
  missing behaviour; the existing 242 tests still pass. Commit
  `test(llm-categorizer)` after the developer accepts.

## Green: implementation

- [x] T7. `adapters/anthropic_categorizer.py`: request, answer
  parsing, failure reasons, stderr line, keyword fallback. Covers:
  AC-LLM-05, 06, 08, 09, 10, 11.
- [x] T8. `startup.py`: `choose_categorizer`, `ConfigurationError`
  and the three messages. Covers: AC-LLM-01, 02, 12, 13, 14.
- [x] T9. `server.py` `main()`: choose the categorizer first, exit 1
  with the message on `ConfigurationError`. Covers: AC-LLM-12, 13,
  14; AC-LLM-03, 04, 07 through the wiring.
- [x] T10. `.mcp.json` variable with `keywords` default; ADR 0005.
  Covers: none (configuration and decision record).
- [x] T11. Definition of done: ruff, mypy, pytest, check_specs;
  domain purity test still green.

## Review and close

- [x] T12. `spec-reviewer` feature review; fix findings or explain
  them.
- [ ] T13. Spec `status: implemented`; README (setup with the `llm`
  extra, privacy note, how to enable it, and how to set up
  credentials: `ant auth login` first, since the credential stays in
  `~/.config/anthropic/` and reaches the stdio server without
  environment variables; `ANTHROPIC_API_KEY` exported in the shell
  as the alternative; never a key in the repo or in `.mcp.json`;
  install and login commands taken from the official docs, not from
  memory); README lessons if anything went wrong. Commit
  `feat(llm-categorizer)` after the developer accepts.
- [ ] T14. Manual check by the developer with a real key: the
  server started from Claude Code via `.mcp.json` with
  `EXPENSE_TRACKER_CATEGORIZER=anthropic` categorizes one expense,
  and the key reaches the server process (plan risk).

## Amendment after the feature review (T12)

Done between T12 and T13: T13 and T14 come after T20.

- [x] T15. Spec: AC-LLM-15 and its AC-LLM-10 sub-case (a 200 reply
  whose body is not a message). Covers: AC-LLM-10, 15.
- [x] T16. Red: test-writer adds the tests for AC-LLM-15 and the new
  AC-LLM-10 sub-case. Commit `test(llm-categorizer)` after the
  developer accepts. Covers: AC-LLM-10, 15.
- [x] T17. Green: the adapter treats those replies as `invalid
  answer`. Covers: AC-LLM-10, 15.
- [x] T18. Spec: a normal reply whose `text` is 5 or null joins
  AC-LLM-15 and its AC-LLM-10 sub-case (final review). Covers:
  AC-LLM-10, 15.
- [ ] T19. Red: test-writer adds those two bodies to both tests.
  Commit `test(llm-categorizer)` after the developer accepts.
  Covers: AC-LLM-10, 15.
- [ ] T20. Green: the answer parsing treats a non-string text as
  `invalid answer`. Covers: AC-LLM-10, 15.

Coverage check: every AC-LLM-01 to 15 appears in at least one task.
