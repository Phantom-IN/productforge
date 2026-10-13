from __future__ import annotations

from pathlib import Path

import pytest

from pflib import merge, workspace
from pflib.merge import REMOVE_MARKER, MergeError


def stage(ws: Path, files: dict[str, str]) -> str:
    run_id, path = workspace.create_staging_run(ws, "phase-planner")
    for rel, text in files.items():
        (path / rel).parent.mkdir(parents=True, exist_ok=True)
        (path / rel).write_text(text)
    return run_id


def test_sections_replace_and_a_new_phase_is_created(tasklet_plan: Path) -> None:
    ws = tasklet_plan
    report = merge.merge(ws, stage(ws, {
        "CLAUDE.md": "## Commands\n\n- `npm test`\n",
        "plans/phase-13-search.md": "# Phase 13 — Search\n",
    }))  # fmt: skip
    claude = (ws / "CLAUDE.md").read_text()
    assert "## Commands\n\n- `npm test`\n" in claude and "## Golden rules" in claude
    assert (ws / "plans/phase-13-search.md").read_text() == "# Phase 13 — Search\n"
    assert sorted(report.documents_updated) == ["CLAUDE.md", "plans/phase-13-search.md"]


def test_remove_marker_deletes_an_open_stage_document(tasklet_plan: Path) -> None:
    ws = tasklet_plan
    report = merge.merge(ws, stage(ws, {"plans/phase-11-billing.md": REMOVE_MARKER + "\n"}))
    assert report.documents_removed == ["plans/phase-11-billing.md"]
    assert not (ws / "plans/phase-11-billing.md").exists()


@pytest.mark.parametrize("rel", ["spec/ARCHITECTURE.md", "research/sources.md"])
def test_records_and_closed_stages_cannot_be_removed(tasklet_plan: Path, rel: str) -> None:
    with pytest.raises(MergeError) as info:
        merge.merge(tasklet_plan, stage(tasklet_plan, {rel: REMOVE_MARKER}))
    assert info.value.code == "BAD_REMOVE"
    assert (tasklet_plan / rel).exists()
