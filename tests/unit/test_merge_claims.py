from __future__ import annotations

from pathlib import Path

from pflib import merge, records, validators, workspace

CLAIM = (
    "### D-?1 — {title}\n- Claim: {claim}\n- Evidence: {ev}\n- Confidence: {conf}\n"
    "- Product impact:\n- Engineering impact:\n- Status: active\n"
)


def stage(ws: Path, text: str) -> str:
    run_id, path = workspace.create_staging_run(ws, "research-agent")
    (path / "research").mkdir()
    (path / "research/DISCOVERY_LEDGER.md").write_text(text)
    return run_id


def ledger(ws: Path) -> records.Document:
    return records.parse_document((ws / "research/DISCOVERY_LEDGER.md").read_text())


def test_same_claim_from_two_runs_is_one_record_with_unioned_evidence(
    tasklet_discovery: Path,
) -> None:
    before = len(ledger(tasklet_discovery).records)
    first = CLAIM.format(
        title="Boards can be filtered by label",
        claim="Boards can be filtered by label.",
        ev="S-017",
        conf="CONFIRMED",
    )
    r1 = merge.merge(tasklet_discovery, stage(tasklet_discovery, first))
    second = CLAIM.format(
        title="Board filtering by label",
        claim="Boards can be filtered by LABEL",
        ev="S-012",
        conf="PROBABLE",
    )
    r2 = merge.merge(tasklet_discovery, stage(tasklet_discovery, second))
    assert r1.new_ids == ["D-045"] and r2.new_ids == [] and r2.id_map == {"D-?1": "D-045"}
    doc = ledger(tasklet_discovery)
    assert len(doc.records) == before + 1
    rec = doc.record("D-045")
    assert rec is not None and rec.get("Evidence") == "S-017, S-012"
    # the canonical confidence is kept; the disagreement is reported, not applied
    assert rec.get("Confidence") == "CONFIRMED"
    assert {
        "id": "D-045",
        "field": "Confidence",
        "kept": "CONFIRMED",
        "staged": "PROBABLE",
    } in r2.conflicts
    assert validators.run(tasklet_discovery) == []  # confidence re-validated on the merged record


def test_unioned_evidence_can_rescue_a_weak_claim_on_preflight(tasklet_discovery: Path) -> None:
    weak = CLAIM.format(
        title="Keyboard shortcuts cover every action",
        claim="Every action has a keyboard shortcut.",
        ev="S-010",
        conf="PROBABLE",
    )
    run = stage(tasklet_discovery, weak)
    pre = merge.preflight(tasklet_discovery, run)
    assert not pre["ok"] and pre["findings"][0]["code"] == "CONFIDENCE_RULE"
    stage_dir = workspace.staging_dir(tasklet_discovery, run) / "research/DISCOVERY_LEDGER.md"
    stage_dir.write_text(weak.replace("S-010", "S-010, S-011"))  # second, independent site
    assert merge.preflight(tasklet_discovery, run)["ok"]
