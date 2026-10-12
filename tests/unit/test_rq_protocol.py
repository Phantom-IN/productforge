"""Research requests (RQ): agents ask, the orchestrator runs a targeted evidence pass, appends to
the closed DISCOVERY stage are allowed, and the requesting role runs once more."""

from __future__ import annotations

from pathlib import Path

import pytest

from pflib import merge, state, validators, workspace
from pflib.merge import MergeError

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/productforge/SKILL.md"
CONTRACT = ROOT / "skills/productforge/references/agent-contract.md"

NEW_EVIDENCE = {
    "research/sources.md": (
        "### S-?1 — Help center: deleting tasks\n- URL: https://help.tasklet.example/delete-tasks\n"
        "- Canonical URL: https://help.tasklet.example/delete-tasks\n- Category: help-center\n"
        "- Tier: 1\n- Authority: High\n- Relevant area: Tasks\n- Published: unknown\n"
        "- Last inspected: 2026-10-12\n- Notes:\n"
    ),
    "research/DISCOVERY_LEDGER.md": (
        "### D-?1 — Only owners and admins delete tasks\n- Claim: Deleting a task is limited to "
        "owners and admins.\n- Evidence: S-?1\n- Confidence: CONFIRMED\n- Product impact:\n"
        "- Engineering impact:\n- Status: active\n"
    ),
}


def stage(ws: Path, role: str, files: dict[str, str]) -> str:
    run_id, path = workspace.create_staging_run(ws, role)
    for rel, text in files.items():
        (path / rel).parent.mkdir(parents=True, exist_ok=True)
        (path / rel).write_text(text)
    return run_id


def test_skill_and_contract_document_research_requests() -> None:
    contract = CONTRACT.read_text(encoding="utf-8")
    assert "RESEARCH REQUESTS" in contract
    skill = SKILL.read_text(encoding="utf-8")
    protocol = skill.split("- **Research requests** in agent summaries", 1)[1].split("\n## ", 1)[0]
    for phrase in (
        "once per command",
        "targeted research-agent run",
        "while DISCOVERY is closed",
        "AMEND_LOCKED",
        "re-run the requesting role **once**",
        "New evidence",
    ):
        assert phrase in protocol, phrase
    model = skill.split("### `/productforge model`", 1)[1].split("\n### ", 1)[0]
    model = " ".join(model.split())
    assert "research requests" in model and "no network" in model


def test_round_trip_appends_to_the_closed_stage(tasklet_product_model: Path) -> None:
    ws = tasklet_product_model
    assert state.load(ws).locks["DISCOVERY"]  # DISCOVERY is closed and locked
    report = merge.merge(ws, stage(ws, "research-agent", NEW_EVIDENCE))
    claim = report.id_map["D-?1"]
    assert sorted(report.new_ids) == [claim, report.id_map["S-?1"]] == ["D-045", "S-021"]
    assert validators.run(ws) == []  # no LOCK_VIOLATION: new records are appends
    # the requesting role runs again and resolves the unknown cell with the new claim
    pm = ws / "spec/PERMISSIONS_MATRIX.md"
    text = pm.read_text()
    old = (
        "- Grants: RL-01 ✓, RL-02 ✓, RL-03 ?, RL-04 ✗\n- Limited means:\n- Evidence: D-027\n"
        "- Confidence: PROBABLE\n- Related unknown: U-009\n"
    )
    assert old in text
    rerun = merge.merge(ws, stage(ws, "domain-architect", {
        "spec/PERMISSIONS_MATRIX.md": (
            "### PR-?1 — Delete task, owners and admins only\n- Resource: E-05\n- Action: delete\n"
            f"- Grants: RL-01 ✓, RL-02 ✓, RL-03 ✗, RL-04 ✗\n- Limited means:\n- Evidence: {claim}\n"
            "- Confidence: CONFIRMED\n\n### AMEND PR-009\n- Status: superseded-by PR-?1\n"
            f"- Why: {claim} settles who may delete tasks.\n"
        ),
    }))  # fmt: skip
    assert rerun.amended == ["PR-009"] and validators.run(ws) == []
    assert "| E-05 Task | delete | ✓ | ✓ | ✗ | ✗ | PR-014 |" in pm.read_text()


def test_amending_a_closed_claim_is_still_refused(tasklet_product_model: Path) -> None:
    run = stage(tasklet_product_model, "research-agent", {
        "research/DISCOVERY_LEDGER.md": "### AMEND D-001\n- Status: rejected\n- Reason: x\n"
                                        "- Why: y\n",
    })  # fmt: skip
    with pytest.raises(MergeError) as info:
        merge.merge(tasklet_product_model, run)
    assert info.value.code == "AMEND_LOCKED"
