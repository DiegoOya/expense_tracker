"""The single architecture rule: the domain imports no infrastructure.

Allowed imports from expense_tracker.domain: the standard library
(except modules that do I/O) and expense_tracker.domain itself.
"""

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOMAIN_DIR = ROOT / "src" / "expense_tracker" / "domain"
DOMAIN_PACKAGE = "expense_tracker.domain"

# Standard-library modules that touch the outside world.
IO_STDLIB = {
    "asyncio",
    "http",
    "io",
    "os",
    "pathlib",
    "shutil",
    "socket",
    "sqlite3",
    "ssl",
    "subprocess",
    "sys",
    "tempfile",
    "urllib",
}


def _module_name(path: Path, package_dir: Path, package: str) -> str:
    rel = path.relative_to(package_dir).with_suffix("")
    parts = [p for p in rel.parts if p != "__init__"]
    return ".".join([package, *parts])


def _resolve(node: ast.ImportFrom, current: str, is_package: bool) -> str:
    if node.level == 0:
        return node.module or ""
    base = current.split(".")
    # In a module, level 1 refers to its package; in __init__, to
    # the package itself.
    drop = node.level - 1 if is_package else node.level
    base = base[: len(base) - drop] if drop else base
    return ".".join([*base, node.module] if node.module else base)


def forbidden_imports(
    package_dir: Path, package: str = DOMAIN_PACKAGE
) -> list[str]:
    """Return 'file:line module' for every forbidden import."""
    problems = []
    for path in sorted(package_dir.rglob("*.py")):
        current = _module_name(path, package_dir, package)
        is_package = path.name == "__init__.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [_resolve(node, current, is_package)]
            else:
                continue
            for module in modules:
                if not _allowed(module, package):
                    rel = path.relative_to(package_dir)
                    problems.append(f"{rel}:{node.lineno} {module}")
    return problems


def _allowed(module: str, package: str) -> bool:
    if module == package or module.startswith(package + "."):
        return True
    top = module.split(".")[0]
    if top == "__future__":
        return True
    return top in sys.stdlib_module_names and top not in IO_STDLIB


def test_domain_imports_no_infrastructure() -> None:
    assert forbidden_imports(DOMAIN_DIR) == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import sqlite3\n", ["bad.py:1 sqlite3"]),
        ("from mcp.server import Server\n", ["bad.py:1 mcp.server"]),
        (
            "from ..adapters import store\n",
            ["bad.py:1 expense_tracker.adapters"],
        ),
        ("import os.path\n", ["bad.py:1 os.path"]),
        ("from decimal import Decimal\n", []),
        ("from .model import Expense\n", []),
        ("from __future__ import annotations\n", []),
    ],
)
def test_checker_detects_forbidden_imports(
    tmp_path: Path, source: str, expected: list[str]
) -> None:
    # Guards against a vacuous rule: the checker must actually flag
    # infrastructure imports, not just pass on an empty domain.
    (tmp_path / "__init__.py").write_text("")
    (tmp_path / "bad.py").write_text(source)
    assert forbidden_imports(tmp_path) == expected
