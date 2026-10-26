# 6. Trunk-based on main, without feature branches or pull requests

- Status: accepted
- Date: 2026-10-26 (recorded after the fact; the practice was used
  from the first commit)

## Context

One developer working with one agent, one feature at a time. Each
feature goes through the same ordered steps (`spec:`, `plan:`,
`tasks:`, `test:`, `feat:`), and the repository is meant to be read as
a record of that process. Branches and pull requests were considered
during the project, after the first tools were done, and the flow was
not changed halfway through.

## Decision

- Commit directly to `main`, in small steps, one commit per SDD phase.
- Review happens before each commit instead of in a pull request: the
  developer accepts the tests (before `test:`) and the code (before
  `feat:`), and the agent's Stop hook runs the whole definition of
  done (ruff, mypy, pytest, check_specs) before every stop.
- Only the developer pushes (`git push` is denied to the agent); CI
  runs the same checks and gitleaks on every push.

## Consequences

- The history is linear and reads in order, phase by phase, which is
  what the repository is for.
- CI checks `main` after the push, not before: a commit that breaks
  the build could reach `main`. It did not happen here, because the
  same checks run locally before each commit, but nothing on GitHub
  would have stopped it.
- The review is recorded in commit messages and in the conversation
  with the agent, not in pull request threads on GitHub.
- The local guardrails (hooks, skills) only act when the agent works;
  a human editing in an IDE relies on CI alone.
- For a team, or for work in parallel: a branch per feature, a pull
  request with CI as a required check and branch protection on
  `main`. The GitHub MCP server in `.mcp.json` would let the agent
  open those pull requests.
