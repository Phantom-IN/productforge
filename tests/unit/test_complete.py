from __future__ import annotations

import json
from pathlib import Path

from conftest import TASKLET

from pflib import gates, state


def test_full_phase_plan_gate_passes() -> None:
    report = gates.evaluate(TASKLET / "PHASE_PLAN_READY", "PHASE_PLAN_READY")
    assert report.passed, [r.to_dict() for r in report.results if not r.passed]
    assert len(report.results) == 7


def test_complete_records_the_final_stage(pf_cli, tasklet_plan: Path) -> None:  # type: ignore[no-untyped-def]
    ws = str(tasklet_plan)
    code, out, _ = pf_cli("complete", "--workspace", ws, "--json")
    assert code == 0 and json.loads(out)["completed"] is False  # report only
    assert state.load(tasklet_plan).stages["PHASE_PLAN_READY"]["completed_at"] is None
    code, out, _ = pf_cli("complete", "--confirmed", "--workspace", ws, "--json")
    assert code == 0 and json.loads(out)["completed"] is True
    assert state.load(tasklet_plan).stages["PHASE_PLAN_READY"]["completed_at"]


def test_complete_refuses_a_failing_gate(pf_cli, tasklet_plan: Path) -> None:  # type: ignore[no-untyped-def]
    (tasklet_plan / "spec/TRACEABILITY.md").write_text("# stale\n")
    code, out, _ = pf_cli("complete", "--confirmed", "--workspace", str(tasklet_plan), "--json")
    assert code == 1 and "G-PP-TRACEABILITY-RENDERED" in json.loads(out)["message"]
    assert state.load(tasklet_plan).stages["PHASE_PLAN_READY"]["completed_at"] is None


def test_complete_only_in_the_final_stage(pf_cli, tasklet_arch: Path) -> None:  # type: ignore[no-untyped-def]
    code, _, _ = pf_cli("complete", "--confirmed", "--workspace", str(tasklet_arch), "--json")
    assert code == 2
