# Tasks: llm-categorizer

Spec: [spec.md](spec.md). Plan: [plan.md](plan.md).
Each task is one commit-sized step. Tick when done.

## Red: tests (test-writer subagent, from spec + plan only)

- [ ] T1. `pyproject.toml`: `llm` extra and `dev` pulling it in;
  reinstall the venv, so the tests can import `anthropic` and
  `httpx2`. Covers: none (enables all).
- [ ] T2. Test doubles in `tests/conftest.py`: `FakeAnthropicAPI`
  with its reply helpers, `DUMMY_CREDENTIAL` and the `clean_env`
  fixture. Covers: none (enables all).
- [ ] T3. Adapter tests in
  `tests/adapters/test_anthropic_categorizer.py`. Covers: AC-LLM-05,
  06, 08, 09, 10, 11.
- [ ] T4. Startup tests in `tests/test_startup.py` (through
  `main()`). Covers: AC-LLM-12, 13, 14.
- [ ] T5. MCP tests in `tests/server/test_llm_categorizer_tool.py`.
  Covers: AC-LLM-01, 02, 03, 04, 07.
- [ ] T6. Run pytest: new tests fail only with import errors or
  missing behaviour; the existing 242 tests still pass. Commit
  `test(llm-categorizer)` after the developer accepts.

## Green: implementation

- [ ] T7. `adapters/anthropic_categorizer.py`: request, answer
  parsing, failure reasons, stderr line, keyword fallback. Covers:
  AC-LLM-05, 06, 08, 09, 10, 11.
- [ ] T8. `startup.py`: `choose_categorizer`, `ConfigurationError`
  and the three messages. Covers: AC-LLM-01, 02, 12, 13, 14.
- [ ] T9. `server.py` `main()`: choose the categorizer first, exit 1
  with the message on `ConfigurationError`. Covers: AC-LLM-12, 13,
  14; AC-LLM-03, 04, 07 through the wiring.
- [ ] T10. `.mcp.json` variable with `keywords` default; ADR 0005.
  Covers: none (configuration and decision record).
- [ ] T11. Definition of done: ruff, mypy, pytest, check_specs;
  domain purity test still green.

## Review and close

- [ ] T12. `spec-reviewer` feature review; fix findings or explain
  them.
- [ ] T13. Spec `status: implemented`; README (setup with the `llm`
  extra, privacy note, how to enable it); README lessons if anything
  went wrong. Commit `feat(llm-categorizer)` after the developer
  accepts.
- [ ] T14. Manual check by the developer with a real key: the
  server started from Claude Code via `.mcp.json` with
  `EXPENSE_TRACKER_CATEGORIZER=anthropic` categorizes one expense,
  and the key reaches the server process (plan risk).

Coverage check: every AC-LLM-01 to 14 appears in at least one task.
