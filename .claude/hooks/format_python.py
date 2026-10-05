#!/usr/bin/env python3
"""PostToolUse hook: format and lint a Python file after Edit/Write.

Runs `ruff format` and `ruff check --fix` on the edited file. If lint
errors remain that ruff cannot fix, exits 2 so the message is shown to
the agent (PostToolUse cannot undo the edit, only report).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    payload = json.load(sys.stdin)
    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path.endswith(".py") or not Path(file_path).is_file():
        return 0

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))
    ruff = project_dir / ".venv" / "bin" / "ruff"
    if not ruff.is_file():
        print(
            "format_python: .venv/bin/ruff not found; skipping. "
            "Run: python3 -m venv .venv && "
            ".venv/bin/pip install -e '.[dev]'",
            file=sys.stderr,
        )
        return 1  # non-blocking notice

    subprocess.run(
        [str(ruff), "format", "--quiet", file_path],
        cwd=project_dir,
        check=False,
    )
    lint = subprocess.run(
        [str(ruff), "check", "--fix", "--quiet", file_path],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if lint.returncode != 0:
        print(
            f"ruff found issues it could not fix in {file_path}:\n"
            f"{lint.stdout}{lint.stderr}",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
