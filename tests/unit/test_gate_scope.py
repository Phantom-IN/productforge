from __future__ import annotations

import json
from pathlib import Path

from conftest import TASKLET

from pflib import gates, state


def failing(ws: Path) -> list[str]:
    return gates.evaluate(ws, "SCOPE_DEFINED").failing()


def details(ws: Path) -> dict[str, str]:
    return {r.id: r.detail for r in gates.evaluate(ws, "SCOPE_DEFINED").results}


def test_passing_fixture_passes_every_condition() -> None:
    report = gates.evaluate(TASKLET / "SCOPE_DEFINED", "SCOPE_DEFINED")
    assert report.passed, [r.to_dict() for r in report.results if not r.passed]
    d = details(TASKLET / "SCOPE_DEFINED")
    assert d["G-SC-ALL-SCORED"] == "all 31 features have one score card"
    assert d["G-SC-OVERRIDES-REASONED"] == "1 overrides, all with reasons"
    assert d["G-SC-REQUIREMENTS-COVER-BUILD"] == "all 18 V1 features are covered by requirements"


def test_failing_fixture_lists_exact_failures() -> None:
    ws = TASKLET / "SCOPE_DEFINED_FAILING"
    assert failing(ws) == ["G-SC-UNKNOWNS-DEFAULTED", "G-SC-CONFLICTS-RESOLVED"]
    d = details(ws)
    assert "U-009, U-010, U-011" in d["G-SC-UNKNOWNS-DEFAULTED"]
    assert "D-045" in d["G-SC-CONFLICTS-RESOLVED"]


def test_a_hand_edited_view_fails_decisions_computed(tasklet_scope: Path) -> None:
    p = tasklet_scope / "research/FEATURE_MATRIX.md"
    p.write_text(p.read_text().replace("| yes | BUILD NOW | 19 |", "| yes | BUILD NOW | 25 |", 1))
    assert "G-SC-DECISIONS-COMPUTED" in failing(tasklet_scope)
    assert "research/FEATURE_MATRIX.md" in details(tasklet_scope)["G-SC-DECISIONS-COMPUTED"]


def test_gate_passing_fixture_advances_to_architecture_locked(pf_cli, tasklet_scope: Path) -> None:  # type: ignore[no-untyped-def]
    code, out, err = pf_cli(
        "advance", "--to", "ARCHITECTURE_LOCKED", "--confirmed", "--workspace", str(tasklet_scope),
        "--json",
    )  # fmt: skip
    assert code == 0, err
    st = state.load(tasklet_scope)
    assert st.state.value == "ARCHITECTURE_LOCKED" and st.locks["SCOPE_DEFINED"]
    assert json.loads(out)["gate"]["passed"] is True
