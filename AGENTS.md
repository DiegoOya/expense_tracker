# AGENTS.md

Rules for any coding agent (and human) working in this repository.

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"   # setup
.venv/bin/ruff format .                  # format (PEP 8 layout)
.venv/bin/ruff check .                   # lint (PEP 8, 79 cols)
.venv/bin/mypy                           # types (strict)
.venv/bin/pytest                         # tests
.venv/bin/python scripts/check_specs.py  # specs <-> tests links
```

## Architecture rule

- `src/expense_tracker/domain/` is pure: it imports only the standard
  library (no I/O modules) and itself. `tests/test_domain_purity.py`
  enforces it. Never weaken that test to make code pass.
- Infrastructure (SQLite, MCP, LLM) lives outside the domain:
  `adapters/` and `server.py`.
- The only port is the categorizer (`domain/categorizer.py`). Do not
  add interfaces, layers or abstractions without an ADR.

## Workflow (spec-driven)

1. Spec: `specs/<feature>/spec.md` from `specs/_template.md`, with
   acceptance criteria `- **AC-<FEAT>-NN** Given ..., when ...,
   then ...`. Status `draft`.
2. Plan: `specs/<feature>/plan.md` (interfaces, files, risks).
3. Tasks: `specs/<feature>/tasks.md` (ordered checklist, each task
   names the AC IDs it covers).
4. Tests first, each linked with `@pytest.mark.spec("AC-<FEAT>-NN")`.
5. Implementation until green; set the spec to `status: implemented`.

One commit per step (`spec:`, `plan:`, `tasks:`, `test:`, `feat:`).
Relevant architecture decisions go in `docs/adr/NNNN-title.md`.

## Code style

- PEP 8: 79-char lines, 72-char docstrings/comments, PEP 8 naming.
  `ruff format` + `ruff check` are the source of truth.
- Type hints everywhere; `mypy --strict` must pass.
- Money is `Decimal` at the edges and integer cents in storage.

## Security

- Never read, print or copy `.env*` or `secrets/`; never dump the
  environment. No credentials in code, tests or commits.
- Only fictitious data. Never real names, accounts or expenses.
- The project must run and pass CI without any API key (fake
  categorizer by default).
- Never `git push`; the human pushes.

## Definition of done

- All commands above pass.
- Every acceptance criterion of the feature has a linked test.
- Spec status updated; ADR added if a decision was made.
- If the agent got something wrong along the way, a short entry in
  README "What went wrong and what I learned".
