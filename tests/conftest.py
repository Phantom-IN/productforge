"""Shared pytest fixtures for ProductForge."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "skills" / "productforge" / "scripts"
PF_SCRIPT = SCRIPTS_DIR / "pf.py"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

CliResult = tuple[int, str, str]


@pytest.fixture
def pf_cli() -> Callable[..., CliResult]:
    """Run ``pf.py`` in a subprocess with the current interpreter.

    Returns ``(exit_code, stdout, stderr)``. Keyword ``cwd`` sets the working directory.
    """

    def run(*args: str, cwd: Path | None = None) -> CliResult:
        proc = subprocess.run(
            [sys.executable, str(PF_SCRIPT), *args],
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            timeout=60,
        )
        return proc.returncode, proc.stdout, proc.stderr

    return run
