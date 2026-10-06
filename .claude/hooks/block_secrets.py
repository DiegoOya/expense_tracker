#!/usr/bin/env python3
"""PreToolUse hook: block Bash commands that touch secrets.

Reads the hook payload from stdin. Exits 2 (block, stderr goes back to
the agent) when a Bash command references a secret path, reads a
credential-like variable ($GITHUB_PAT, os.getenv("API_KEY")) or dumps
the environment. Exits 0 otherwise.

This is a guardrail, not a security boundary: it inspects command
text, so a determined process can evade it. See
docs/adr/0004-hooks-are-guardrails-not-security.md.
"""

from __future__ import annotations

import json
import re
import shlex
import sys

OPERATORS = {";", "&&", "||", "|", "|&", "&"}
# Subshells and redirections also start a new command or file operand.
SEPARATOR_CHARS = set("();<>")
ENV_DUMPERS = {"printenv"}
# Whole simple commands that print every variable.
VARIABLE_DUMPS = (
    ["env"],
    ["set"],
    ["export"],
    ["export", "-p"],
    ["declare", "-p"],
    ["declare", "-x"],
)
ALLOWED_ENV_FILES = {".env.example"}

# A variable name is sensitive when one of its "_"-separated parts is
# one of these, so GITHUB_PAT and ANTHROPIC_API_KEY match but PATH and
# KEYBOARD_LAYOUT do not.
SENSITIVE_NAME_PARTS = {
    "CREDENTIALS",
    "KEY",
    "PASSWD",
    "PASSWORD",
    "PAT",
    "SECRET",
    "TOKEN",
}

# A quoted secret path inside a token, e.g. python -c "open('.env')".
QUOTED_SECRET = re.compile(
    r"""['"](?:\./)?(?:\.env(?:\.[\w.-]+)?|secrets(?:/[^'"]*)?)['"]"""
)
# Shell expansion: $NAME, ${NAME}, ${NAME:-default}.
VAR_EXPANSION = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)")
# Lookup from code: os.environ['NAME'], os.environ.get("NAME"),
# os.getenv("NAME").
ENV_LOOKUP = re.compile(
    r"(?:environ(?:\.get)?|getenv)\W{1,3}([A-Za-z_][A-Za-z0-9_]*)"
)


def _is_sensitive_name(name: str) -> bool:
    parts = name.upper().split("_")
    return any(part in SENSITIVE_NAME_PARTS for part in parts)


def _sensitive_variable(command: str) -> str | None:
    """Return a credential-like variable the command would read."""
    for pattern in (VAR_EXPANSION, ENV_LOOKUP):
        for match in pattern.finditer(command):
            if _is_sensitive_name(match.group(1)):
                return match.group(1)
    return None


def _is_env_file(name: str) -> bool:
    if name in ALLOWED_ENV_FILES:
        return False
    return name == ".env" or name.startswith(".env.")


def _secret_in_path(token: str) -> str | None:
    """Return the offending path if `token` looks like a secret path."""
    for part in token.split("="):
        parts = [p for p in part.split("/") if p not in ("", ".")]
        if not parts:
            continue
        if _is_env_file(parts[-1]):
            return part
        if "secrets" in parts:
            return part
    return None


def _tokenize(command: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    return list(lexer)


def find_violation(command: str) -> str | None:
    """Return a human-readable reason if `command` must be blocked."""
    variable = _sensitive_variable(command)
    if variable is not None:
        return f"reads credential-like variable '{variable}'"
    try:
        tokens = _tokenize(command)
    except ValueError:
        # Unbalanced quotes: fall back to a raw-text check.
        tokens = command.split()

    # A segment is one simple command between operators, so we can
    # tell which word is in command position.
    segment: list[str] = []
    for token in [*tokens, ";"]:
        if token in OPERATORS or set(token) <= SEPARATOR_CHARS:
            if segment and segment[0] in ENV_DUMPERS:
                return f"'{segment[0]}' dumps environment variables"
            if segment in VARIABLE_DUMPS:
                dump = " ".join(segment)
                return f"'{dump}' dumps environment variables"
            segment = []
            continue
        segment.append(token)

        path = _secret_in_path(token)
        if path is not None:
            return f"references secret path '{path}'"
        match = QUOTED_SECRET.search(token)
        if match is not None and not _is_allowed_literal(match.group(0)):
            return f"references secret path {match.group(0)}"
    return None


def _is_allowed_literal(literal: str) -> bool:
    name = literal.strip("'\"").removeprefix("./")
    return name in ALLOWED_ENV_FILES


def main() -> int:
    payload = json.load(sys.stdin)
    if payload.get("tool_name") != "Bash":
        return 0
    command = payload.get("tool_input", {}).get("command", "")
    reason = find_violation(command)
    if reason is None:
        return 0
    print(
        f"Blocked by .claude/hooks/block_secrets.py: command {reason}. "
        "The agent must never read secrets (.env*, secrets/, "
        "credential-like variables such as *_PAT or *_TOKEN) or dump "
        "the environment. Use .env.example to learn the expected keys; "
        "to check a variable is set, ask the user.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
