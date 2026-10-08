from __future__ import annotations

import json
from pathlib import Path

import pytest

import pf
from pflib import merge, state, validators, workspace


def advance(ws: Path, gate_control: object, capsys: pytest.CaptureFixture[str]) -> None:
    assert pf.main(["advance", "--to", "PRODUCT_MODEL", "--confirmed", "--workspace", str(ws)]) == 0
    capsys.readouterr()
    assert state.load(ws).state == state.State.PRODUCT_MODEL


def codes(ws: Path) -> list[str]:
    return [f.code for f in validators.run(ws)]


def test_advancing_the_fixture_locks_every_discovery_record(
    tasklet_discovery: Path, gate_control: object, capsys: pytest.CaptureFixture[str]
) -> None:
    advance(tasklet_discovery, gate_control, capsys)
    locked = state.load(tasklet_discovery).locks["DISCOVERY"]
    assert len([i for i in locked if i.startswith("S-")]) == 16
    assert len([i for i in locked if i.startswith("D-")]) == 18
    assert len([i for i in locked if i.startswith("U-")]) == 3
    assert codes(tasklet_discovery) == []


def test_editing_a_locked_record_is_a_violation(
    tasklet_discovery: Path, gate_control: object, capsys: pytest.CaptureFixture[str]
) -> None:
    advance(tasklet_discovery, gate_control, capsys)
    ledger = tasklet_discovery / "research/DISCOVERY_LEDGER.md"
    ledger.write_text(ledger.read_text().replace("Target users are small teams.", "Enterprises."))
    found = validators.run(tasklet_discovery)
    assert [(f.code, f.record_id) for f in found] == [("LOCK_VIOLATION", "D-018")]
    assert "reopen DISCOVERY" in found[0].message


def test_appending_records_and_evidence_is_allowed_but_removal_is_not(
    tasklet_discovery: Path, gate_control: object, capsys: pytest.CaptureFixture[str]
) -> None:
    advance(tasklet_discovery, gate_control, capsys)
    run_id, path = workspace.create_staging_run(tasklet_discovery, "research-agent")
    (path / "research").mkdir()
    (path / "research/DISCOVERY_LEDGER.md").write_text(
        "### D-?1 — Tasks can be assigned to one member\n"
        "- Claim: A task has at most one assignee.\n"
        "- Evidence: S-002\n- Confidence: CONFIRMED\n- Product impact:\n- Engineering impact:\n"
        "- Status: active\n\n"
        "### D-?2 — Tasks can be archived\n- Claim: Finished tasks can be archived.\n"
        "- Evidence: S-001\n- Confidence: CONFIRMED\n- Product impact:\n- Engineering impact:\n"
        "- Status: active\n"
    )
    report = merge.merge(tasklet_discovery, run_id)
    assert report.id_map == {"D-?1": "D-001", "D-?2": "D-019"}  # evidence union + append
    assert codes(tasklet_discovery) == []
    ledger = tasklet_discovery / "research/DISCOVERY_LEDGER.md"
    assert "- Evidence: S-001, S-002\n" in ledger.read_text()
    ledger.write_text(
        ledger.read_text().replace("- Evidence: S-001, S-002\n", "- Evidence: S-002\n")
    )
    found = validators.run(tasklet_discovery)
    assert [(f.code, f.record_id) for f in found] == [("LOCK_VIOLATION", "D-001")]
    assert "references removed: S-001" in found[0].message


def test_deleted_locked_record(
    tasklet_discovery: Path, gate_control: object, capsys: pytest.CaptureFixture[str]
) -> None:
    advance(tasklet_discovery, gate_control, capsys)
    unknowns = tasklet_discovery / "research/UNKNOWNS.md"
    text = unknowns.read_text()
    unknowns.write_text(text[: text.index("### U-003")])
    found = validators.run(tasklet_discovery)
    assert ("LOCK_DELETED", "U-003") in [(f.code, f.record_id) for f in found]


def test_reopen_drops_locks_so_edits_are_allowed(
    tasklet_discovery: Path, gate_control: object, capsys: pytest.CaptureFixture[str]
) -> None:
    advance(tasklet_discovery, gate_control, capsys)
    pf.main(["reopen", "DISCOVERY", "--reason", "fix D-018", "--workspace", str(tasklet_discovery)])
    capsys.readouterr()
    ledger = tasklet_discovery / "research/DISCOVERY_LEDGER.md"
    ledger.write_text(ledger.read_text().replace("Target users are small teams.", "Small teams."))
    assert codes(tasklet_discovery) == []


def test_corrupt_state_is_left_to_the_gate(tasklet_discovery: Path) -> None:
    (tasklet_discovery / ".productforge/state.json").write_text(json.dumps({"bad": 1}))
    assert codes(tasklet_discovery) == []
