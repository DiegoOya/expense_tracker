@AGENTS.md

# Claude Code specifics

- New feature or MCP tool: run the `/add-mcp-tool` skill. To write or
  rewrite only a spec: the `write-spec` skill.
- Delegate test writing to the `test-writer` subagent (it cannot read
  `src/`, so give it the spec and plan paths, not code).
- Before a `feat:` commit, run the `spec-reviewer` subagent and fix
  what it reports, or explain to the user why not.
- Hooks in `.claude/settings.json` format Python on every edit and
  run tests + spec check when you stop. If the Stop hook blocks you,
  fix the failure; do not disable or edit hooks to get past it.
- Do not edit `.claude/` (settings, hooks, agents, skills) unless the
  user asks for it explicitly.
- Stop at the end of each SDD phase and wait for the user's review.
