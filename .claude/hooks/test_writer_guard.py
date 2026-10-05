#!/usr/bin/env python3
"""PreToolUse hook for the test-writer subagent.

Enforces the two properties that make test-writer worth being a
subagent:

* it may only write under tests/;
* it may not read the implementation under src/, so tests are derived
  from the spec and plan, not from the code they are meant to check.

Exits 2 (block, reason to the agent) on a violation, 0 otherwise.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

WRITE_TOOLS = {"Write", "Edit"}
READ_TOOLS = {"Read"}


def _relative(path: str, project_dir: Path) -> Path | None:
    """Return `path` relative to the project, or None if outside."""
    resolved = (project_dir / path).resolve()
    try:
        return resolved.relative_to(project_dir.resolve())
    except ValueError:
        return None


def find_violation(
    tool_name: str, file_path: str, project_dir: Path
) -> str | None:
    rel = _relative(file_path, project_dir)
    top = rel.parts[:1] if rel is not None else None
    if tool_name in WRITE_TOOLS and top != ("tests",):
        return f"test-writer may only write under tests/, not {file_path}"
    if tool_name in READ_TOOLS and top == ("src",):
        return (
            f"test-writer may not read the implementation ({file_path}); "
            "derive tests from specs/<feature>/spec.md and plan.md"
        )
    return None


def main() -> int:
    payload = json.load(sys.stdin)
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))
    file_path = payload.get("tool_input", {}).get("file_path", "")
    reason = find_violation(
        payload.get("tool_name", ""), file_path, project_dir
    )
    if reason is None:
        return 0
    print(f"Blocked by test_writer_guard.py: {reason}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
