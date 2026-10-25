from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pflib import merge, records, state, validators, workspace
from pflib.merge import MergeError

NEW_CLAIM = (
    "### D-?1 — Tasks can repeat on a schedule\n"
    "- Claim: Tasks can be set to repeat on a schedule.\n"
    "- Evidence: S-020, S-010\n- Confidence: CONFIRMED\n- Product impact:\n- Engineering impact:\n"
    "- Status: active\n"
)


def stage(ws: Path, text: str, rel: str = "research/DISCOVERY_LEDGER.md") -> str:
    run_id, path = workspace.create_staging_run(ws, "research-agent")
    (path / rel).parent.mkdir(parents=True, exist_ok=True)
    (path / rel).write_text(text)
    return run_id


def tree_hash(ws: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(ws.rglob("*")):
        if p.is_file() and "staging" not in p.parts and p.name != "history.log":
            h.update(p.relative_to(ws).as_posix().encode() + p.read_bytes())
    return h.hexdigest()


def claim(ws: Path, record_id: str) -> records.Record:
    doc = records.parse_document((ws / "research/DISCOVERY_LEDGER.md").read_text())
    rec = doc.record(record_id)
    assert rec is not None
    return rec


def test_supersede_a_duplicate_in_the_open_stage(tasklet_discovery: Path) -> None:
    text = NEW_CLAIM + (
        "\n### AMEND D-005\n- Status: superseded-by D-?1\n"
        "- Why: D-005 states the same fact; the launch post (S-020) confirms it.\n"
    )
    report = merge.merge(tasklet_discovery, stage(tasklet_discovery, text))
    assert report.new_ids == ["D-045"] and report.amended == ["D-005"]
    assert claim(tasklet_discovery, "D-005").get("Status") == "superseded-by D-045"
    assert claim(tasklet_discovery, "D-005").get("Claim") == (
        "Users report creating tasks that repeat on a schedule."
    )  # nothing else changed
    event = workspace.read_history(tasklet_discovery)[-2]
    assert event["event"] == "amend" and event["id"] == "D-005"
    assert event["fields"] == {"Status": "superseded-by D-045"} and "S-020" in event["why"]
    assert report.ignored_prose_lines == 0
    assert validators.run(tasklet_discovery) == []


def test_mark_a_late_found_conflict_on_both_sides(tasklet_discovery: Path) -> None:
    text = (
        "### AMEND D-040\n- Status: conflicting-with D-?1\n- Why: the new pricing page disagrees.\n"
        "\n### D-?1 — The free plan allows three members\n"
        "- Claim: The free plan is limited to three "
        "members.\n- Evidence: S-006\n- Confidence: CONFIRMED\n- Product impact:\n"
        "- Engineering impact:\n- Status: conflicting-with D-040\n"
        "- Context: Free plan member limit\n"
        "- Resolution: S-006 was updated after S-004.\n"
    )
    report = merge.merge(tasklet_discovery, stage(tasklet_discovery, text))
    assert report.amended == ["D-040"]
    assert claim(tasklet_discovery, "D-040").get("Status") == "conflicting-with D-045"
    assert validators.run(tasklet_discovery) == []  # symmetric, resolved


def test_amendment_and_evidence_union_on_the_same_record(tasklet_discovery: Path) -> None:
    text = (
        "### D-?1 — Releases ship weekly\n- Claim: The changelog shows a weekly release cadence.\n"
        "- Evidence: S-020\n- Confidence: CONFIRMED\n- Product impact:\n- Engineering impact:\n"
        "- Status: active\n\n### AMEND D-017\n- Resolution: Cadence confirmed by two posts.\n"
        "- Why: record the corroboration.\n"
    )
    report = merge.merge(tasklet_discovery, stage(tasklet_discovery, text))
    rec = claim(tasklet_discovery, "D-017")
    assert report.deduped == 1 and report.amended == ["D-017"]
    assert rec.get("Evidence") == "S-005, S-020" and rec.get("Resolution").startswith("Cadence")


@pytest.mark.parametrize(
    "block, code",
    [
        ("### AMEND D-999\n- Status: rejected\n- Reason: x\n- Why: y\n", "AMEND_TARGET_MISSING"),
        ("### AMEND D-005\n- Claim: rewritten\n- Why: y\n", "AMEND_FIELD_NOT_ALLOWED"),
        ("### AMEND D-005\n- Why: nothing to change\n", "AMEND_FIELD_NOT_ALLOWED"),
        ("### AMEND D-005\n- Status: rejected\n- Reason: wrong product\n", "AMEND_NO_REASON"),
        ("### AMEND D-005\n- Status: superseded-by D-?7\n- Why: y\n", "DANGLING_PROVISIONAL"),
    ],
)
def test_refusals_write_nothing(tasklet_discovery: Path, block: str, code: str) -> None:
    run = stage(tasklet_discovery, block)
    before = tree_hash(tasklet_discovery)
    with pytest.raises(MergeError) as info:
        merge.merge(tasklet_discovery, run)
    assert info.value.code == code
    assert tree_hash(tasklet_discovery) == before


def test_closed_stage_records_cannot_be_amended(tasklet_discovery: Path) -> None:
    st = state.load(tasklet_discovery)
    st.locks["DISCOVERY"] = state.snapshot_locks(tasklet_discovery, state.State.DISCOVERY)
    state.transition(st, state.State.PRODUCT_MODEL, "2026-10-09T00:00:00Z")
    state.save(tasklet_discovery, st)
    run = stage(tasklet_discovery, "### AMEND D-005\n- Status: rejected\n- Reason: x\n- Why: y\n")
    before = tree_hash(tasklet_discovery)
    with pytest.raises(MergeError) as info:
        merge.merge(tasklet_discovery, run)
    assert info.value.code == "AMEND_LOCKED" and "reopen DISCOVERY" in info.value.message
    assert tree_hash(tasklet_discovery) == before


def test_malformed_amendment_line_is_a_parse_error(tasklet_discovery: Path) -> None:
    run = stage(tasklet_discovery, "### AMEND D-005\n- Status rejected\n- Why: y\n")
    with pytest.raises(records.RecordParseError):
        merge.merge(tasklet_discovery, run)


def test_amendment_blocks_inside_fences_are_ignored() -> None:
    text = "```\n### AMEND D-005\n- Status: rejected\n```\n"
    assert records.parse_amendments(text) == []


def test_superseding_a_near_duplicate_clears_the_warning(tasklet_discovery: Path) -> None:
    dup = (
        "### D-?1 — Tasks can be assigned to one member.\n- Claim: Exactly one member may own a "
        "task.\n- Evidence: S-001\n- Confidence: CONFIRMED\n- Product impact:\n"
        "- Engineering impact:\n- Status: active\n"
    )
    merge.merge(tasklet_discovery, stage(tasklet_discovery, dup))
    assert [f.code for f in validators.run(tasklet_discovery)] == ["NEAR_DUPLICATE_TITLE"]
    amend = "### AMEND D-045\n- Status: superseded-by D-001\n- Why: same fact as D-001.\n"
    merge.merge(tasklet_discovery, stage(tasklet_discovery, amend))
    assert validators.run(tasklet_discovery) == []
