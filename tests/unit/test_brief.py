from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pflib import brief, merge, workspace
from pflib.errors import PFError

BAD_CLAIM = (
    "### D-?1 — Exports exist\n- Claim: Tasks can be exported.\n- Evidence: S-010\n"
    "- Confidence: CONFIRMED\n- Product impact:\n- Engineering impact:\n- Status: active\n"
)
GOOD_CLAIM = BAD_CLAIM.replace("S-010", "S-001")


def tree_hash(ws: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(ws.rglob("*")):
        if p.is_file() and "staging" not in p.parts:
            h.update(p.relative_to(ws).as_posix().encode() + p.read_bytes())
    return h.hexdigest()


def stage(ws: Path, run_id: str | None, text: str) -> str:
    if run_id is None:
        run_id, _ = workspace.create_staging_run(ws, "research-agent")
    target = workspace.staging_dir(ws, run_id) / "research" / "DISCOVERY_LEDGER.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return run_id


def test_brief_renders_workspace_values(tasklet_discovery: Path) -> None:
    b = brief.render(
        tasklet_discovery,
        role="research-agent",
        task="Collect official docs.",
        partition="official-docs",
        inputs=["research/sources.md", "research/FEATURE_MATRIX.md"],
        templates=["agent-brief.md"],
        budget="at most 10 sources",
    )
    assert b.staging_path.is_dir() and b.staging_path.name == b.run_id
    assert not b.repair and b.findings == 0 and b.max_repair_loops == 2
    for expected in (
        str(b.staging_path),
        "task tracking for small teams",
        "Tasklet (https://tasklet.example)",
        "official-docs",
        "at most 10 sources",
        str(brief.CONTRACT),
        "Open stage: DISCOVERY",
        f"{tasklet_discovery / 'research/sources.md'}\n",
        "FEATURE_MATRIX.md (does not exist yet)",
        "Collect official docs.",
    ):
        assert expected in b.text, expected
    assert "{{" not in b.text
    assert f"RUN {b.run_id} · ROLE research-agent" in b.text


def test_brief_errors(tasklet_discovery: Path, tmp_path: Path) -> None:
    with pytest.raises(PFError) as info:
        brief.render(tasklet_discovery, role="research-agent", task=" ")
    assert info.value.code == "BAD_BRIEF"
    with pytest.raises(PFError) as info:
        brief.render(tasklet_discovery, role="research-agent", task="x", templates=["nope.md"])
    assert info.value.code == "BAD_TEMPLATE"
    with pytest.raises(PFError) as info:
        brief.render(
            tasklet_discovery,
            role="research-agent",
            task="x",
            run_id="20260101T000000-research-agent-abcd",
        )
    assert info.value.code == "NO_SUCH_RUN"
    with pytest.raises(PFError) as info:
        workspace.resolve_workspace(str(tmp_path))
    assert info.value.code == "NO_WORKSPACE"


def test_preflight_reports_findings_without_touching_the_workspace(tasklet_discovery: Path) -> None:
    run_id = stage(tasklet_discovery, None, BAD_CLAIM)
    before = tree_hash(tasklet_discovery)  # after staging (creating a run logs to history)
    result = merge.preflight(tasklet_discovery, run_id)
    assert result["ok"] is False and result["errors"] == 1
    (f,) = result["findings"]
    assert f["code"] == "CONFIDENCE_RULE" and f["record_id"] == "D-045"
    assert result["report"]["new_ids"] == ["D-045"]
    assert tree_hash(tasklet_discovery) == before
    assert workspace.staging_dir(tasklet_discovery, run_id).is_dir()  # still pending


def test_repair_brief_lists_findings_in_provisional_ids(tasklet_discovery: Path) -> None:
    run_id = stage(tasklet_discovery, None, BAD_CLAIM)
    b = brief.render(tasklet_discovery, role="research-agent", task="Fix it.", run_id=run_id)
    assert b.repair and b.findings == 1 and b.run_id == run_id
    assert "- ERROR CONFIDENCE_RULE D-?1: D-?1: CONFIRMED needs a Tier ≤ 2 source" in b.text
    assert "D-045" not in b.text
    stage(tasklet_discovery, run_id, GOOD_CLAIM)  # the agent fixes its staged file
    assert merge.preflight(tasklet_discovery, run_id)["ok"] is True
    fixed = brief.render(tasklet_discovery, role="research-agent", task="Fix it.", run_id=run_id)
    assert fixed.findings == 0 and "## Validator findings to fix\n\nnone\n" in fixed.text


def test_repair_brief_reports_merge_errors(tasklet_discovery: Path) -> None:
    run_id = stage(tasklet_discovery, None, BAD_CLAIM.replace("S-010", "S-?9"))
    result = merge.preflight(tasklet_discovery, run_id)
    assert result["ok"] is False and result["merge_error"]["error"] == "DANGLING_PROVISIONAL"
    b = brief.render(tasklet_discovery, role="research-agent", task="Fix it.", run_id=run_id)
    assert (
        "- DANGLING_PROVISIONAL: provisional references with no staged definition: S-?9" in b.text
    )


def test_empty_existing_run_renders_a_normal_brief(tasklet_discovery: Path) -> None:
    run_id, _ = workspace.create_staging_run(tasklet_discovery, "research-agent")
    b = brief.render(tasklet_discovery, role="research-agent", task="Go.", run_id=run_id)
    assert b.run_id == run_id and not b.repair
