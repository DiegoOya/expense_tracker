#!/usr/bin/env python3
"""Validate that specs and tests are linked.

Rules:

1. Every specs/<feature>/spec.md has a front matter `status` of
   draft, planned or implemented.
2. Every spec declares at least one acceptance criterion, written as a
   list item starting with a bold ID: `- **AC-ADD-01** ...`.
3. Acceptance criterion IDs are unique across all specs.
4. Every criterion of an `implemented` spec is referenced by at least
   one test via `@pytest.mark.spec("AC-ADD-01")`.
5. Every `pytest.mark.spec` reference points to an existing criterion.

Usage: python scripts/check_specs.py [--root PATH]
Exits 1 and prints one line per problem when a rule is broken.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

STATUSES = {"draft", "planned", "implemented"}
AC_LINE = re.compile(r"^\s*[-*]\s+\*\*(AC-[A-Z0-9]+-\d{2,})\*\*", re.M)
FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


@dataclass(frozen=True)
class Spec:
    path: Path
    status: str | None
    criteria: tuple[str, ...]


def parse_spec(path: Path) -> Spec:
    text = path.read_text(encoding="utf-8")
    status = None
    match = FRONT_MATTER.match(text)
    if match:
        for line in match.group(1).splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "status":
                status = value.strip()
    return Spec(path, status, tuple(AC_LINE.findall(text)))


def find_test_references(tests_dir: Path) -> dict[str, list[str]]:
    """Map each referenced AC ID to the tests that reference it."""
    refs: dict[str, list[str]] = {}
    for path in sorted(tests_dir.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and _is_spec_mark(node)):
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(
                    arg.value, str
                ):
                    rel = path.relative_to(tests_dir.parent)
                    where = f"{rel}:{node.lineno}"
                    refs.setdefault(arg.value, []).append(where)
    return refs


def _is_spec_mark(node: ast.Call) -> bool:
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "spec"
        and isinstance(func.value, ast.Attribute)
        and func.value.attr == "mark"
    )


def check(root: Path) -> list[str]:
    problems: list[str] = []
    specs = [parse_spec(p) for p in sorted(root.glob("specs/*/spec.md"))]
    refs = find_test_references(root / "tests")

    owner: dict[str, Path] = {}
    for spec in specs:
        rel = spec.path.relative_to(root)
        if spec.status not in STATUSES:
            problems.append(
                f"{rel}: front matter 'status' must be one of "
                f"{sorted(STATUSES)}, got {spec.status!r}"
            )
        if not spec.criteria:
            problems.append(f"{rel}: no acceptance criteria found")
        for ac in spec.criteria:
            if ac in owner:
                problems.append(
                    f"{rel}: {ac} already defined in "
                    f"{owner[ac].relative_to(root)}"
                )
            owner[ac] = spec.path
            if spec.status == "implemented" and ac not in refs:
                problems.append(f"{rel}: {ac} has no test")

    for ac, places in sorted(refs.items()):
        if ac not in owner:
            for place in places:
                problems.append(f"{place}: unknown criterion {ac}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    problems = check(args.root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"check_specs: {len(problems)} problem(s)", file=sys.stderr)
        return 1
    print("check_specs: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
