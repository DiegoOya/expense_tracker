"""Hooks are code, so they get tests.

Each hook is run as Claude Code runs it: a subprocess that receives
the JSON payload on stdin and answers with its exit code.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / ".claude" / "hooks"


def run_hook(
    name: str, payload: dict[str, object], cwd: Path = ROOT
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOKS / name)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=cwd,
        env={"CLAUDE_PROJECT_DIR": str(cwd), "PATH": "/usr/bin:/bin"},
        check=False,
    )


def bash(command: str) -> dict[str, object]:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


@pytest.mark.parametrize(
    "command",
    [
        "cat .env",
        "grep TOKEN .env",
        "source .env && echo ok",
        "cat config/.env.local",
        "docker run --env-file=.env image",
        "python -c \"print(open('.env').read())\"",
        "ls secrets",
        "cp secrets/key.pem /tmp/k",
        "base64 < ./secrets/token",
        "printenv",
        "printenv GITHUB_PAT",
        "env",
        "ls && env | grep PAT",
        "echo $(printenv)",
    ],
)
def test_block_secrets_blocks(command: str) -> None:
    result = run_hook("block_secrets.py", bash(command))
    assert result.returncode == 2, result.stderr
    assert "Blocked" in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "cat .env.example",
        ".venv/bin/pytest -q",
        "git commit -m 'block .env and secrets access'",
        "env PYTHONPATH=src python -m expense_tracker.server",
        "ls -la",
        "grep -rn environment src/",
    ],
)
def test_block_secrets_allows(command: str) -> None:
    result = run_hook("block_secrets.py", bash(command))
    assert result.returncode == 0, result.stderr


def test_block_secrets_ignores_other_tools() -> None:
    payload = {"tool_name": "Read", "tool_input": {"file_path": ".env"}}
    assert run_hook("block_secrets.py", payload).returncode == 0


@pytest.mark.parametrize(
    ("tool", "path", "expected"),
    [
        ("Write", "tests/test_x.py", 0),
        ("Edit", "tests/domain/test_y.py", 0),
        ("Write", "src/expense_tracker/domain/x.py", 2),
        ("Write", "tests/../src/x.py", 2),
        ("Edit", "/etc/passwd", 2),
        ("Read", "src/expense_tracker/server.py", 2),
        ("Read", "specs/add-expense/spec.md", 0),
        ("Read", "tests/test_hooks.py", 0),
    ],
)
def test_test_writer_guard(tool: str, path: str, expected: int) -> None:
    payload = {"tool_name": tool, "tool_input": {"file_path": path}}
    result = run_hook("test_writer_guard.py", payload)
    assert result.returncode == expected, result.stderr


def test_format_python_formats_file(tmp_path: Path) -> None:
    ruff = ROOT / ".venv" / "bin" / "ruff"
    if not ruff.is_file():
        pytest.skip("needs the project virtualenv")
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "ruff").symlink_to(ruff)
    target = tmp_path / "ugly.py"
    target.write_text("x=1\ny = [ 1,2 ]\n")
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
    result = run_hook("format_python.py", payload, cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert target.read_text() == "x = 1\ny = [1, 2]\n"


def test_format_python_reports_unfixable_lint(tmp_path: Path) -> None:
    ruff = ROOT / ".venv" / "bin" / "ruff"
    if not ruff.is_file():
        pytest.skip("needs the project virtualenv")
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "ruff").symlink_to(ruff)
    target = tmp_path / "bad.py"
    target.write_text("print(undefined_name)\n")
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(target)}}
    result = run_hook("format_python.py", payload, cwd=tmp_path)
    assert result.returncode == 2
    assert "F821" in result.stderr


def test_format_python_ignores_non_python(tmp_path: Path) -> None:
    target = tmp_path / "notes.md"
    target.write_text("# hi\n")
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
    assert run_hook("format_python.py", payload, cwd=tmp_path).returncode == 0
