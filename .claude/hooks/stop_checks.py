#!/usr/bin/env python3
"""Stop hook: run the definition-of-done checks before the agent stops.

Runs ruff format --check, ruff check, mypy, pytest and the spec
validator (the same commands as CI).

On failure, exits 2 and writes the failure to stderr, which Claude
Code feeds back to the agent so it keeps working.

Loop protection: when `stop_hook_active` is true the agent is already
continuing because of this hook. In that case we still run the checks
but never block again; a remaining failure is reported to the user as
a system message instead.

Skipped when nothing relevant changed (no modified *.py, *.md, *.toml
or specs/ files in `git status`) or when the virtualenv does not
exist yet.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

MAX_OUTPUT_LINES = 60


def _relevant_changes(project_dir: Path) -> bool:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    for line in status.stdout.splitlines():
        path = line[3:].split(" -> ")[-1].strip('"')
        # ruff also formats Python code blocks inside Markdown.
        if path.endswith((".py", ".md", ".toml")) or path.startswith("specs/"):
            return True
    return False


def _run(cmd: list[str], project_dir: Path) -> tuple[bool, str]:
    result = subprocess.run(
        cmd, cwd=project_dir, capture_output=True, text=True, check=False
    )
    output = (result.stdout + result.stderr).strip().splitlines()
    tail = "\n".join(output[-MAX_OUTPUT_LINES:])
    return result.returncode == 0, tail


def main() -> int:
    payload = json.load(sys.stdin)
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))
    venv_bin = project_dir / ".venv" / "bin"
    if not (venv_bin / "pytest").is_file():
        return 0
    if not _relevant_changes(project_dir):
        return 0

    # The full definition of done from AGENTS.md, cheapest first. All
    # checks run, so the agent sees every failure at once.
    checks = {
        "ruff format": [str(venv_bin / "ruff"), "format", "--check", "."],
        # No cache: ruff's first-party detection depends on which
        # modules exist on disk, so cached results can be stale.
        "ruff check": [str(venv_bin / "ruff"), "check", "--no-cache", "."],
        "mypy": [str(venv_bin / "mypy")],
        "pytest": [str(venv_bin / "pytest"), "-x", "-q"],
        "check_specs": [
            str(venv_bin / "python"),
            "scripts/check_specs.py",
        ],
    }
    failures = []
    for name, cmd in checks.items():
        ok, output = _run(cmd, project_dir)
        if not ok:
            failures.append(f"## {name} failed\n{output}")
    if not failures:
        return 0

    report = "\n\n".join(failures)
    if payload.get("stop_hook_active"):
        message = (
            "Stop hook: checks still failing after one retry; "
            "not blocking again.\n" + report
        )
        print(json.dumps({"systemMessage": message}))
        return 0

    print(
        "Checks failed. Fix them before finishing, or explain why "
        "the failure is expected (e.g. a red TDD step).\n\n" + report,
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
