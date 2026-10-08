"""Shared pytest fixtures for ProductForge."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "skills" / "productforge" / "scripts"
PF_SCRIPT = SCRIPTS_DIR / "pf.py"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

CliResult = tuple[int, str, str]


@pytest.fixture
def pf_cli(tmp_path_factory: pytest.TempPathFactory) -> Callable[..., CliResult]:
    """Run ``pf.py`` in a subprocess with the current interpreter.

    Returns ``(exit_code, stdout, stderr)``. Keyword ``cwd`` sets the working directory; by
    default it is a fresh empty temp dir, so a command can never write into the repository.
    """
    default_cwd = tmp_path_factory.mktemp("cli-cwd")

    def run(*args: str, cwd: Path | None = None) -> CliResult:
        proc = subprocess.run(
            [sys.executable, str(PF_SCRIPT), *args],
            capture_output=True,
            text=True,
            cwd=str(cwd or default_cwd),
            timeout=60,
        )
        return proc.returncode, proc.stdout, proc.stderr

    return run


class GateControl:
    """Stand-in implementations for every declared-but-unbuilt gate condition.

    ``outcomes[condition_id] = False`` makes that condition fail; everything else passes.
    """

    def __init__(self) -> None:
        self.outcomes: dict[str, bool] = {}

    def fail(self, *condition_ids: str) -> None:
        for cid in condition_ids:
            self.outcomes[cid] = False

    def reset(self) -> None:
        self.outcomes.clear()


@pytest.fixture
def gate_control(monkeypatch: pytest.MonkeyPatch) -> GateControl:
    from pflib import gates

    control = GateControl()
    for stage, declared in gates.EXPECTED.items():
        table = dict(gates.REGISTRY[stage])
        for cid, description, _phase in declared:
            if cid not in table:

                def check(ws: Path, cid: str = cid) -> gates.ConditionResult:
                    ok = control.outcomes.get(cid, True)
                    return gates.ConditionResult(ok, "stub pass" if ok else "stub fail")

                table[cid] = gates.GateCondition(cid, description, check)
        monkeypatch.setitem(gates.REGISTRY, stage, table)
    return control


@pytest.fixture
def new_ws(tmp_path: Path) -> Path:
    """A freshly initialised workspace (DISCOVERY open, scope accepted)."""
    from pflib import scaffold

    ws, _ = scaffold.init_workspace(
        "https://tasklet.example", out=str(tmp_path / "tl"), scope="task tracking"
    )
    return ws
