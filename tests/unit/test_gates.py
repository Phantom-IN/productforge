from __future__ import annotations

from pathlib import Path

import pytest

from pflib import gates, scaffold, state, workspace
from pflib.errors import CheckFailed


def test_unbuilt_conditions_fail_as_not_built(new_ws: Path) -> None:
    report = gates.evaluate(new_ws, "SCOPE_DEFINED")
    by_id = {r.id: r for r in report.results}
    assert by_id["G-SC-ALL-SCORED"].status == gates.STATUS_NOT_BUILT
    assert by_id["G-SC-ALL-SCORED"].detail == "not built yet (Phase 13)"
    assert not report.passed


def test_discovery_conditions_are_all_built(new_ws: Path) -> None:
    report = gates.evaluate(new_ws, "DISCOVERY")
    assert all(r.status in (gates.STATUS_PASS, gates.STATUS_FAIL) for r in report.results)
    by_id = {r.id: r for r in report.results}
    assert by_id["G-SCOPE-SET"].passed and by_id["G-STATE-FILE-VALID"].passed
    assert not by_id["G-DISC-TIER1"].passed and not report.passed


def test_every_stage_declares_generic_conditions() -> None:
    for stage in state.ADVANCEABLE:
        ids = [cid for cid, _, _ in gates.EXPECTED[stage.value]]
        assert ids[:3] == ["G-STATE-FILE-VALID", "G-NO-UNMERGED-STAGING", "G-VALIDATE-CLEAN"]
        assert len(ids) == len(set(ids))


def test_stub_control_passes_and_fails(new_ws: Path, gate_control: object) -> None:
    assert gates.evaluate(new_ws, "DISCOVERY").passed
    gate_control.fail("G-DISC-MIN-CLAIMS")  # type: ignore[attr-defined]
    report = gates.evaluate(new_ws, "DISCOVERY")
    assert report.failing() == ["G-DISC-MIN-CLAIMS"]


def test_register_rejects_undeclared_ids() -> None:
    cond = gates.GateCondition("G-MADE-UP", "x", lambda ws: gates.ConditionResult(True))
    with pytest.raises(ValueError):
        gates.register("DISCOVERY", cond)


def test_check_errors_are_reported_not_raised(
    new_ws: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(ws: Path) -> gates.ConditionResult:
        raise CheckFailed("parse failure in sources.md")

    table = dict(gates.REGISTRY["DISCOVERY"])
    table["G-DISC-TIER1"] = gates.GateCondition("G-DISC-TIER1", "tier1", boom)
    monkeypatch.setitem(gates.REGISTRY, "DISCOVERY", table)
    row = next(r for r in gates.evaluate(new_ws, "DISCOVERY").results if r.id == "G-DISC-TIER1")
    assert row.status == gates.STATUS_ERROR and row.detail == "parse failure in sources.md"


def test_unmerged_staging_blocks(new_ws: Path) -> None:
    run_id, _ = workspace.create_staging_run(new_ws, "research-agent")
    row = next(
        r for r in gates.evaluate(new_ws, "DISCOVERY").results if r.id == "G-NO-UNMERGED-STAGING"
    )
    assert not row.passed and run_id in row.detail


def test_scope_condition(tmp_path: Path) -> None:
    ws, _ = scaffold.init_workspace("https://tasklet.example", out=str(tmp_path / "w"))
    rows = {r.id: r for r in gates.evaluate(ws, "DISCOVERY").results}
    assert not rows["G-SCOPE-SET"].passed and "no scope" in rows["G-SCOPE-SET"].detail
    scaffold.set_scope(ws, "task tracking", accepted=False, source="recommended")
    rows = {r.id: r for r in gates.evaluate(ws, "DISCOVERY").results}
    assert "not been accepted" in rows["G-SCOPE-SET"].detail
    scaffold.set_scope(ws, "task tracking", accepted=True, source="recommended")
    assert {r.id: r for r in gates.evaluate(ws, "DISCOVERY").results}["G-SCOPE-SET"].passed


def test_corrupt_state_file_fails_condition(new_ws: Path) -> None:
    state.state_path(new_ws).write_text("{}")
    rows = {r.id: r for r in gates.evaluate(new_ws, "DISCOVERY").results}
    assert not rows["G-STATE-FILE-VALID"].passed


def test_stage_gates_reference_lists_every_condition() -> None:
    ref = Path(__file__).resolve().parents[2] / "skills/productforge/references/stage-gates.md"
    text = ref.read_text(encoding="utf-8")
    for stage, declared in gates.EXPECTED.items():
        section = text.split(f"### {stage}\n", 1)[1].split("\n### ", 1)[0]
        for cid, _desc, phase in declared:
            assert f"| `{cid}` |" in section and f"Phase {phase}" in section, (stage, cid)
