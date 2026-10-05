"""Tests for scripts/check_specs.py, the spec <-> test validator."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def _load_checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_specs", ROOT / "scripts" / "check_specs.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_specs"] = module
    spec.loader.exec_module(module)
    return module


check_specs = _load_checker()


def write_spec(root: Path, feature: str, status: str, *acs: str) -> None:
    lines = [f"- **{ac}** Given x, when y, then z." for ac in acs]
    body = f"---\nstatus: {status}\n---\n# {feature}\n\n" + "\n".join(lines)
    path = root / "specs" / feature / "spec.md"
    path.parent.mkdir(parents=True)
    path.write_text(body + "\n")


def write_test(root: Path, name: str, *acs: str) -> None:
    tests = root / "tests"
    tests.mkdir(exist_ok=True)
    funcs = [
        f'@pytest.mark.spec("{ac}")\ndef test_{i}():\n    pass\n'
        for i, ac in enumerate(acs)
    ]
    (tests / name).write_text("import pytest\n\n" + "\n".join(funcs))


def test_draft_spec_without_tests_is_ok(tmp_path: Path) -> None:
    write_spec(tmp_path, "add-expense", "draft", "AC-ADD-01")
    assert check_specs.check(tmp_path) == []


def test_implemented_spec_needs_a_test_per_criterion(tmp_path: Path) -> None:
    write_spec(
        tmp_path, "add-expense", "implemented", "AC-ADD-01", "AC-ADD-02"
    )
    write_test(tmp_path, "test_add.py", "AC-ADD-01")
    assert check_specs.check(tmp_path) == [
        "specs/add-expense/spec.md: AC-ADD-02 has no test"
    ]


def test_implemented_spec_fully_covered(tmp_path: Path) -> None:
    write_spec(
        tmp_path, "add-expense", "implemented", "AC-ADD-01", "AC-ADD-02"
    )
    write_test(tmp_path, "test_add.py", "AC-ADD-01", "AC-ADD-02")
    assert check_specs.check(tmp_path) == []


def test_unknown_criterion_in_tests(tmp_path: Path) -> None:
    write_spec(tmp_path, "add-expense", "draft", "AC-ADD-01")
    write_test(tmp_path, "test_add.py", "AC-ADD-99")
    assert check_specs.check(tmp_path) == [
        "tests/test_add.py:3: unknown criterion AC-ADD-99"
    ]


def test_invalid_status_and_missing_criteria(tmp_path: Path) -> None:
    write_spec(tmp_path, "add-expense", "done")
    problems = check_specs.check(tmp_path)
    assert len(problems) == 2
    assert "status" in problems[0]
    assert "no acceptance criteria" in problems[1]


def test_duplicate_criterion_ids(tmp_path: Path) -> None:
    write_spec(tmp_path, "a", "draft", "AC-X-01")
    write_spec(tmp_path, "b", "draft", "AC-X-01")
    assert check_specs.check(tmp_path) == [
        "specs/b/spec.md: AC-X-01 already defined in specs/a/spec.md"
    ]


def test_real_repository_passes() -> None:
    assert check_specs.check(ROOT) == []
