from __future__ import annotations

import json
from pathlib import Path

from conftest import TASKLET

from pflib import gates, state


def failing(ws: Path) -> list[str]:
    return gates.evaluate(ws, "ARCHITECTURE_LOCKED").failing()


def test_passing_fixture_passes_every_condition() -> None:
    report = gates.evaluate(TASKLET / "ARCHITECTURE_LOCKED", "ARCHITECTURE_LOCKED")
    assert report.passed, [r.to_dict() for r in report.results if not r.passed]
    d = {r.id: r.detail for r in report.results}
    assert d["G-AR-REQUIREMENTS-ADDRESSED"] == "all 11 requirements addressed (0 by convention)"
    assert d["G-AR-INVARIANTS"] == "7 invariants, all enforced"
    assert d["G-AR-REPO-STRUCTURE"].startswith("repository structure declares 13 paths")


def test_failing_fixture_lists_exact_failures() -> None:
    assert failing(TASKLET / "ARCHITECTURE_LOCKED_FAILING") == ["G-AR-INVARIANTS"]


def test_open_stack_choice_fails(tasklet_arch: Path) -> None:
    p = tasklet_arch / "spec/ARCHITECTURE.md"
    p.write_text(
        p.read_text().replace("| Files | S3-compatible object storage |", "| Files | TBD |")
    )
    assert set(failing(tasklet_arch)) == {"G-VALIDATE-CLEAN", "G-AR-STACK-COMPLETE"}


def test_gate_passing_fixture_advances_to_phase_plan_ready(pf_cli, tasklet_arch: Path) -> None:  # type: ignore[no-untyped-def]
    code, out, err = pf_cli(
        "advance", "--to", "PHASE_PLAN_READY", "--confirmed", "--workspace", str(tasklet_arch),
        "--json",
    )  # fmt: skip
    assert code == 0, err
    st = state.load(tasklet_arch)
    assert st.state.value == "PHASE_PLAN_READY" and st.locks["ARCHITECTURE_LOCKED"]
    assert json.loads(out)["gate"]["passed"] is True
