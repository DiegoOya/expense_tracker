# 4. Hooks are guardrails, not a security boundary

- Status: accepted
- Date: 2026-10-05

## Context

The agent must never read secrets. Claude Code offers permission
rules, hooks and an OS-level sandbox.

## Decision

Layered, and honest about each layer:

1. **No secrets in the repo.** Nothing needs a key to run or pass CI;
   gitleaks scans the full history in CI.
2. **Permission deny rules** for `.env*` and `secrets/`. They also
   cover common file commands in Bash (`cat`, `head`, `sed`, ...).
3. **PreToolUse hook** (`block_secrets.py`) for what deny rules miss:
   `grep`, `source`, `python -c "open('.env')"`, `printenv`, ... It
   runs before permission checks and blocks with exit code 2.
4. **The sandbox** is the real boundary if strong isolation is needed.

The hook inspects command text, so it can be evaded (e.g. building the
path at runtime). It exists to stop accidents, not attackers.

## Consequences

- False positives are possible (e.g. `ls secrets` in an unrelated
  context); the message tells the agent why it was blocked.
- Hooks are code: they have tests in `tests/test_hooks.py`.
