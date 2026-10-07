---
name: add-mcp-tool
description: Add a new MCP tool to the expense-tracker server following the full spec-driven flow (spec, plan, tasks, tests, implementation, review), with the user reviewing the tests and the code before they are committed, one commit per phase.
argument-hint: "<tool_name> [what it should do]"
disable-model-invocation: true
---

# Add an MCP tool (SDD)

Tool: $ARGUMENTS
Feature slug: the tool name in kebab-case (`add_expense` ->
`add-expense`).

Follow the phases in order. **Stop and wait for the user** where it
says STOP. Never commit tests or code the user has not accepted.

## 1. Spec

Use the `write-spec` skill. Then run the `spec-reviewer` subagent on
the spec only (ask it to check that every criterion is verifiable).
Fix its findings. Commit `spec(<slug>): ...`.

## 2. Plan -> `specs/<slug>/plan.md`

Short, concrete:
- Domain: new types and pure functions, with exact signatures. These
  signatures are the contract `test-writer` codes against.
- Adapters: storage changes (schema, queries); categorizer usage.
- MCP tool: name, parameters and types, structured output, and how
  domain errors map to `ToolError` (the only exception whose message
  reaches the client in MCP SDK v2).
- Test strategy per layer, and which AC each layer covers.
- Risks and whether an ADR is needed.

Commit `plan(<slug>): ...`.

## 3. Tasks -> `specs/<slug>/tasks.md`

Ordered checklist, small enough for one commit-sized step each. Every
task names the AC IDs it covers; every AC appears in at least one
task. Set the spec to `status: planned`. Commit `tasks(<slug>): ...`.

STOP: show the plan and tasks to the user.

## 4. Tests (red)

Delegate to the `test-writer` subagent with the paths of `spec.md` and
`plan.md`. It writes tests under `tests/` linked with
`@pytest.mark.spec(...)`. Read what it wrote: its report is not
evidence. Run `.venv/bin/pytest` and confirm they fail for the right
reason (missing code, not a broken test).

STOP: show the user the test files (`git diff --stat`, the tests per
AC, anything test-writer flagged as ambiguous). The tests are red on
purpose, so the Stop hook blocks the first stop: answer that the
failure is the expected red step and stop again. Commit
`test(<slug>): ...` only after the user accepts.

## 5. Implementation (green)

Domain first, then adapters, then `server.py`. Tick tasks in
`tasks.md` as you go. Do not modify the tests to make them pass; if a
test is wrong, say so and fix it in a separate, explained step.

Run every command in AGENTS.md "Definition of done".

## 6. Review

Run the `spec-reviewer` subagent on the whole feature. Fix findings
or explain why not. Set the spec to `status: implemented`;
`check_specs.py` must pass.

STOP: show the user the code for review (`git diff --stat`, key
changes per layer, check results, reviewer verdict and what was fixed
or left). Make any requested changes and stop again. Commit
`feat(<slug>): ...` only after the user accepts.

## 7. Retrospective

If anything went wrong (wrong assumption, hook block, reviewer
finding, flaky test), add a short entry to README "What went wrong
and what I learned": what happened, why, what changed.

STOP: summarise for the user.
