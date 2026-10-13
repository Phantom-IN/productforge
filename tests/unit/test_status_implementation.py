from __future__ import annotations

import json
from pathlib import Path

from pflib import metrics, plans


def test_not_detected_while_every_phase_is_not_started(tasklet_plan: Path) -> None:
    assert plans.implementation_detected(tasklet_plan, gate_passed=True) is False


def test_detected_once_a_phase_has_started(capsys, gate_control, tasklet_plan: Path) -> None:  # type: ignore[no-untyped-def]
    import pf  # in-process, so the stubbed gate applies

    p = tasklet_plan / "plans/README.md"
    link = "[phase-00-repository-foundation.md](phase-00-repository-foundation.md)"
    p.write_text(p.read_text().replace(f"| {link} | Not started |", f"| {link} | In progress |"))
    assert plans.implementation_detected(tasklet_plan, gate_passed=True) is True
    assert plans.implementation_detected(tasklet_plan, gate_passed=False) is False
    assert pf.main(["status", "--workspace", str(tasklet_plan), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["implementation_detected"] is True
    assert pf.main(["status", "--workspace", str(tasklet_plan)]) == 0
    assert "IMPLEMENTATION: phases are being executed" in capsys.readouterr().out


def test_funnel_counts_phases(tasklet_plan: Path, tasklet_arch: Path) -> None:
    assert metrics.funnel(tasklet_plan)["phases"] == 13
    assert metrics.funnel(tasklet_arch)["phases"] is None
