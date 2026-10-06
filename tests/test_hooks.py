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
        # Expanding a credential-like variable prints its value.
        "echo $GITHUB_PAT",
        'echo "${GITHUB_PAT}"',
        'curl -H "Authorization: Bearer $GITHUB_TOKEN" x',
        "echo ${ANTHROPIC_API_KEY:-none}",
        "echo $DB_PASSWORD",
        "echo x$AWS_SECRET_ACCESS_KEY",
        "python3 -c \"import os; print(os.environ['GITHUB_PAT'])\"",
        "python3 -c 'import os; print(os.getenv(\"MY_TOKEN\"))'",
        # Dumping every variable.
        "set",
        "export",
        "export -p",
        "declare -p",
        "declare -x",
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
        # Non-credential variables must keep working.
        "echo $PATH",
        "echo $HOME $KEYBOARD_LAYOUT ${PWD}",
        "export EXPENSE_TRACKER_DB=data/test.db",
        "set -euo pipefail",
        "python3 -c \"import os; print(os.environ['HOME'])\"",
        # Mentioning a name without expanding it is fine.
        "grep -n GITHUB_PAT README.md .mcp.json",
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


STOP_CHECKS = ("ruff format", "ruff check", "mypy", "pytest", "check_specs")


def make_project(tmp_path: Path, failing: set[str] = frozenset()) -> Path:
    """A git repo whose .venv/bin tools exit 1 for the `failing` checks.

    The tools are shell stubs that print their name, so tests can see
    which checks ran and which failures were reported.
    """

    def code(check: str) -> int:
        return 1 if check in failing else 0

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    bin_dir = tmp_path / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    stubs = {
        "ruff": (
            'if [ "$1" = format ]; then echo "ran ruff format"; '
            f"exit {code('ruff format')}; fi\n"
            f'echo "ran ruff check"; exit {code("ruff check")}\n'
        ),
        "mypy": f'echo "ran mypy"; exit {code("mypy")}\n',
        "pytest": f'echo "ran pytest"; exit {code("pytest")}\n',
        "python": f'echo "ran check_specs"; exit {code("check_specs")}\n',
    }
    for name, body in stubs.items():
        stub = bin_dir / name
        stub.write_text("#!/bin/sh\n" + body)
        stub.chmod(0o755)
    return tmp_path


def stop(
    project: Path, active: bool = False
) -> subprocess.CompletedProcess[str]:
    payload = {"hook_event_name": "Stop", "stop_hook_active": active}
    return run_hook("stop_checks.py", payload, cwd=project)


def test_stop_skips_when_nothing_relevant_changed(tmp_path: Path) -> None:
    project = make_project(tmp_path, failing=set(STOP_CHECKS))
    result = stop(project)
    assert result.returncode == 0
    assert "ran" not in result.stdout + result.stderr


@pytest.mark.parametrize("changed", ["src/x.py", "specs/a/spec.md", "a.md"])
def test_stop_runs_every_check_on_relevant_changes(
    tmp_path: Path, changed: str
) -> None:
    project = make_project(tmp_path, failing=set(STOP_CHECKS))
    (project / changed).parent.mkdir(parents=True, exist_ok=True)
    (project / changed).write_text("x\n")
    result = stop(project)
    assert result.returncode == 2
    for check in STOP_CHECKS:
        assert f"## {check} failed" in result.stderr


def test_stop_reports_only_failing_checks(tmp_path: Path) -> None:
    project = make_project(tmp_path, failing={"ruff format", "mypy"})
    (project / "x.py").write_text("x = 1\n")
    result = stop(project)
    assert result.returncode == 2
    assert "## ruff format failed" in result.stderr
    assert "## mypy failed" in result.stderr
    assert "## pytest failed" not in result.stderr


def test_stop_passes_when_all_checks_pass(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    (project / "x.py").write_text("x = 1\n")
    assert stop(project).returncode == 0


def test_stop_does_not_block_twice(tmp_path: Path) -> None:
    project = make_project(tmp_path, failing={"pytest"})
    (project / "x.py").write_text("x = 1\n")
    result = stop(project, active=True)
    assert result.returncode == 0
    message = json.loads(result.stdout)["systemMessage"]
    assert "## pytest failed" in message
