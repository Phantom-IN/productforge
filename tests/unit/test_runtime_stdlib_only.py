"""Guard for CLAUDE.md golden rule 9: runtime code imports only the standard library.

Every ``.py`` file under ``skills/`` and ``hooks/`` is parsed (never imported) and each
absolute import must be either a standard-library module or first-party (``pflib``).
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIRS = [REPO_ROOT / "skills", REPO_ROOT / "hooks"]
FIRST_PARTY = {"pflib"}


_STDLIB = set(sys.stdlib_module_names) | set(sys.builtin_module_names)


def is_stdlib(module: str) -> bool:
    return module.split(".")[0] in _STDLIB


def imports_of(source: str) -> Iterator[tuple[int, str]]:
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.lineno, node.module


def violations(source: str) -> list[tuple[int, str]]:
    return [
        (line, mod)
        for line, mod in imports_of(source)
        if mod.split(".")[0] not in FIRST_PARTY and not is_stdlib(mod)
    ]


def runtime_files() -> list[Path]:
    return sorted(
        p
        for d in RUNTIME_DIRS
        if d.exists()
        for p in d.rglob("*.py")
        if "__pycache__" not in p.parts
    )


def test_runtime_files_exist() -> None:
    names = {p.name for p in runtime_files()}
    assert {"pf.py", "__init__.py", "errors.py", "io.py"} <= names


def test_runtime_imports_are_stdlib_only() -> None:
    found = {
        str(path.relative_to(REPO_ROOT)): bad
        for path in runtime_files()
        if (bad := violations(path.read_text(encoding="utf-8")))
    }
    assert found == {}, f"non-stdlib imports in runtime code: {found}"


def test_detector_flags_third_party_imports() -> None:
    source = "import json\nimport requests\nfrom yaml import safe_load\nfrom pflib.io import emit\n"
    assert violations(source) == [(2, "requests"), (3, "yaml")]


def test_detector_accepts_stdlib_and_relative_imports() -> None:
    source = "import os.path\nfrom urllib.robotparser import RobotFileParser\nfrom . import x\n"
    assert violations(source) == []
