from __future__ import annotations

from pathlib import Path

import pytest

from pflib import merge, render, validators, workflows, workspace
from pflib.merge import MergeError

FLOW = "research/workflows/W-001-create-a-task.md"
NEW_STEPS = (
    "## Steps\n\n1. [observed] Member opens the board and adds a task to a status column — D-037\n"
    "2. [observed] Member enters a title; the task starts in To do — D-024\n"
    "3. [implied-system] Check the member may create tasks in this workspace — F-022\n"
    "4. [implied-system] Persist the task with its workspace and optional project — F-001, D-002\n"
)


def stage(ws: Path, text: str, rel: str = "research/workflows/revise.md") -> str:
    run_id, path = workspace.create_staging_run(ws, "ux-analyst")
    (path / rel).parent.mkdir(parents=True, exist_ok=True)
    (path / rel).write_text(text)
    return run_id


def test_revision_replaces_body_sections_and_keeps_the_header(tasklet_product_model: Path) -> None:
    ws = tasklet_product_model
    before = (ws / FLOW).read_text()
    report = merge.merge(
        ws, stage(ws, f"### REVISE W-001\n- Why: the docs show fewer steps\n\n{NEW_STEPS}")
    )
    after = (ws / FLOW).read_text()
    assert report.revised == ["W-001"] and report.new_ids == []
    assert after.split("## Steps", 1)[0] == before.split("## Steps", 1)[0]  # header unchanged
    steps, _ = workflows.parse_steps(after)
    assert len(steps) == 4 and "## Variations & edge cases" in after  # other sections kept
    event = workspace.read_history(ws)[-2]
    assert event["event"] == "revise" and event["sections"] == ["Steps"] and "fewer" in event["why"]
    index = render.regions((ws / "research/README.md").read_text())["workflows"]
    assert "| W-001 | Create a task | Member | F-001, F-004, F-008 | CONFIRMED | 2 | 2 |" in index
    assert validators.run(ws) == []


HEAD = "### REVISE W-001\n- Why: x\n\n"


@pytest.mark.parametrize(
    "text, code",
    [
        ("### REVISE W-099\n- Why: x\n\n## Steps\n\n1. [observed] a — D-001\n",
         "REVISE_TARGET_MISSING"),
        ("### REVISE W-001\n\n## Steps\n\n1. [observed] a — D-001\n", "REVISE_NO_REASON"),
        (HEAD + "No section here.\n", "BAD_REVISION"),
        (HEAD + "## Steps\n\n1. [observed] a — D-?1\n", "DANGLING_PROVISIONAL"),
    ],
)  # fmt: skip
def test_bad_revisions_are_refused(tasklet_product_model: Path, text: str, code: str) -> None:
    before = (tasklet_product_model / FLOW).read_text()
    with pytest.raises(MergeError) as info:
        merge.merge(tasklet_product_model, stage(tasklet_product_model, text))
    assert info.value.code == code and (tasklet_product_model / FLOW).read_text() == before


def test_closed_stage_records_cannot_be_revised(tasklet_scope: Path) -> None:
    with pytest.raises(MergeError) as info:
        merge.merge(
            tasklet_scope, stage(tasklet_scope, f"### REVISE W-001\n- Why: x\n\n{NEW_STEPS}")
        )
    assert info.value.code == "REVISE_LOCKED" and "reopen PRODUCT_MODEL" in info.value.message


def test_titles_that_differ_by_number_are_not_near_duplicates(tasklet_discovery: Path) -> None:
    p = tasklet_discovery / "research/sources.md"
    extra = "".join(
        f"\n### S-1{n} — Release post: Tasklet v3.{n}\n- URL: https://tasklet.example/blog/v3-{n}\n"
        f"- Canonical URL: https://tasklet.example/blog/v3-{n}\n- Category: product-blog\n"
        "- Tier: 2\n"
        "- Authority: Medium\n- Relevant area: Releases\n- Published: unknown\n"
        "- Last inspected: 2026-10-13\n- Notes:\n"
        for n in (2, 4)
    )
    p.write_text(p.read_text() + extra)
    assert "NEAR_DUPLICATE_TITLE" not in {f.code for f in validators.run(tasklet_discovery)}
