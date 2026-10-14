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
# the stdlib halves of observe mode (redact, server) are imported directly by tests/observe/
OBSERVE_DIR = REPO_ROOT / "observe"
if str(OBSERVE_DIR) not in sys.path:
    sys.path.append(str(OBSERVE_DIR))

CliResult = tuple[int, str, str]


@pytest.fixture
def pf_cli(tmp_path_factory: pytest.TempPathFactory) -> Callable[..., CliResult]:
    """Run ``pf.py`` in a subprocess with the current interpreter.

    Returns ``(exit_code, stdout, stderr)``. Keyword ``cwd`` sets the working directory; by
    default it is a fresh empty temp dir, so a command can never write into the repository.
    """
    default_cwd = tmp_path_factory.mktemp("cli-cwd")

    def run(*args: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> CliResult:
        import os

        proc = subprocess.run(
            [sys.executable, str(PF_SCRIPT), *args],
            capture_output=True,
            text=True,
            cwd=str(cwd or default_cwd),
            timeout=60,
            env={**os.environ, **(env or {})},
        )
        return proc.returncode, proc.stdout, proc.stderr

    return run


class GateControl:
    """Stand-ins for every stage-specific gate condition (built or not), so lifecycle tests do
    not depend on each phase's content rules. The generic conditions (state file, staging,
    validation) stay real.

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
    gates.load_conditions()
    real = {"G-STATE-FILE-VALID", "G-NO-UNMERGED-STAGING", "G-VALIDATE-CLEAN"}
    for stage, declared in gates.EXPECTED.items():
        table = dict(gates.REGISTRY[stage])
        for cid, description, _phase in declared:
            if cid not in real:

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


def copy_snapshot(name: str, dest: Path) -> Path:
    import shutil

    shutil.copytree(TASKLET / name, dest)
    return dest


@pytest.fixture
def tasklet_product_model(tmp_path: Path) -> Path:
    """A writable copy of the Tasklet PRODUCT_MODEL fixture workspace."""
    return copy_snapshot("PRODUCT_MODEL", tmp_path / "tasklet-pm")


@pytest.fixture
def tasklet_plan(tmp_path: Path) -> Path:
    """A writable copy of the Tasklet PHASE_PLAN_READY fixture workspace."""
    return copy_snapshot("PHASE_PLAN_READY", tmp_path / "tasklet-pp")


@pytest.fixture
def tasklet_arch(tmp_path: Path) -> Path:
    """A writable copy of the Tasklet ARCHITECTURE_LOCKED fixture workspace."""
    return copy_snapshot("ARCHITECTURE_LOCKED", tmp_path / "tasklet-ar")


@pytest.fixture
def tasklet_scope(tmp_path: Path) -> Path:
    """A writable copy of the Tasklet SCOPE_DEFINED fixture workspace."""
    return copy_snapshot("SCOPE_DEFINED", tmp_path / "tasklet-sc")


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
    """Apply an overlay to workspace ``ws``; returns the expected finding code.

    The body may continue into further files with
    ``<!-- next target: <path> mode: <mode> -->`` separator lines.
    """
    import re

    from pflib import records, state

    meta, body = read_overlay(path)
    if "lock" in meta:
        st = state.load(ws)
        st.locks[meta["lock"]] = state.snapshot_locks(ws, state.State(meta["lock"]))
        state.save(ws, st)
    parts = re.split(r"^<!-- next target: (\S+) mode: (.+?) -->\n", body, flags=re.M)
    steps = [(meta["target"], meta["mode"], parts[0])]
    steps += [(parts[i], parts[i + 1], parts[i + 2]) for i in range(1, len(parts), 3)]
    for target_rel, mode_spec, chunk in steps:
        target = ws / target_rel
        text = target.read_text(encoding="utf-8") if target.is_file() else ""
        mode, _, record_id = mode_spec.partition(" ")
        if mode == "write":  # create or overwrite the whole file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(chunk, encoding="utf-8")
            continue
        if mode == "append":
            text = text.rstrip("\n") + "\n\n" + chunk
        else:
            doc = records.parse_document(text)
            rec = doc.record(record_id)
            assert rec is not None, (path, record_id)
            replacement = [chunk] if mode == "replace" else []
            text = "".join(doc.lines[: rec.start] + replacement + doc.lines[rec.end :])
        target.write_text(text, encoding="utf-8")
    if meta.get("render", "yes") != "no":
        from pflib import render

        render.render_all(ws)  # merge always re-renders; keep views fresh like real runs do
    return meta["expect"]
