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


FIXTURES = REPO_ROOT / "tests" / "fixtures"
TASKLET = FIXTURES / "workspaces" / "tasklet"
INVALID = FIXTURES / "invalid"


@pytest.fixture
def tasklet_discovery(tmp_path: Path) -> Path:
    """A writable copy of the Tasklet DISCOVERY fixture workspace."""
    import shutil

    dest = tmp_path / "tasklet"
    shutil.copytree(TASKLET / "DISCOVERY", dest)
    return dest


def read_overlay(path: Path) -> tuple[dict[str, str], str]:
    """Parse an invalid-case overlay: an HTML-comment header of ``key: value`` lines + body."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("<!--\n"), path
    header, body = text[5:].split("-->\n", 1)
    meta = dict(line.split(": ", 1) for line in header.strip().splitlines())
    return meta, body


def apply_overlay(ws: Path, path: Path) -> str:
    """Apply an overlay to workspace ``ws``; returns the expected finding code."""
    from pflib import records, state

    meta, body = read_overlay(path)
    if "lock" in meta:
        st = state.load(ws)
        st.locks[meta["lock"]] = state.snapshot_locks(ws, state.State(meta["lock"]))
        state.save(ws, st)
    target = ws / meta["target"]
    text = target.read_text(encoding="utf-8")
    mode, _, record_id = meta["mode"].partition(" ")
    if mode == "append":
        text = text.rstrip("\n") + "\n\n" + body
    else:
        doc = records.parse_document(text)
        rec = doc.record(record_id)
        assert rec is not None, (path, record_id)
        replacement = [body] if mode == "replace" else []
        text = "".join(doc.lines[: rec.start] + replacement + doc.lines[rec.end :])
    target.write_text(text, encoding="utf-8")
    return meta["expect"]
