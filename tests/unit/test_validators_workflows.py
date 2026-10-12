from __future__ import annotations

from pathlib import Path

import pytest

from pflib import render, validators, workflows

FLOW = "research/workflows/W-001-create-a-task.md"


def codes(ws: Path) -> list[str]:
    return [f.code for f in validators.run(ws)]


def test_fixture_workflows_are_clean(tasklet_product_model: Path) -> None:
    assert len(workflows.workflow_files(tasklet_product_model)) == 8
    assert validators.run(tasklet_product_model) == []


def test_create_task_surfaces_the_core_system_steps(tasklet_product_model: Path) -> None:
    steps, bad = workflows.parse_steps((tasklet_product_model / FLOW).read_text())
    assert bad == [] and [s.number for s in steps] == list(range(1, 10))
    implied = " ".join(s.text.lower() for s in steps if s.tag == "implied-system")
    assert sum(s.tag == "implied-system" for s in steps) >= 4
    for need in ("persist", "activity", "index", "notify"):
        assert need in implied, need
    assert all(s.refs for s in steps if s.tag == "observed")


def test_step_grammar() -> None:
    text = (
        "## Steps\n\n1. [observed] Opens the board — D-037, S-001\n"
        "2. [implied-system] Persist it\n3. [guessed] Something\n4) not a step\n"
    )
    steps, bad = workflows.parse_steps(text)
    assert [(s.number, s.tag, s.refs) for s in steps] == [
        (1, "observed", ("D-037", "S-001")),
        (2, "implied-system", ()),
    ]
    assert bad == ["3. [guessed] Something"]
    assert workflows.parse_steps("## Other\n\n1. [observed] x — D-1\n") == ([], [])


def edit(ws: Path, old: str, new: str) -> None:
    p = ws / FLOW
    text = p.read_text()
    assert old in text, old
    p.write_text(text.replace(old, new, 1))


@pytest.mark.parametrize(
    "old, new, code",
    [
        ("2. [observed]", "3. [observed]", "BAD_STEPS"),
        ("1. [observed]", "1. [seen]", "BAD_STEP_TAG"),
        ("status column — D-037", "status column", "OBSERVED_STEP_NO_EVIDENCE"),
        ("— F-019", "— F-999", "DANGLING_REF"),
    ],
)
def test_step_findings(tasklet_product_model: Path, old: str, new: str, code: str) -> None:
    edit(tasklet_product_model, old, new)
    assert code in codes(tasklet_product_model)


def test_no_system_steps_is_a_warning_unless_none_is_declared(tasklet_product_model: Path) -> None:
    p = tasklet_product_model / "research/workflows/W-008-archive-a-project.md"
    text = p.read_text()
    lines = [ln for ln in text.splitlines() if "[implied-system]" not in ln]
    p.write_text("\n".join(lines) + "\n")
    assert render.render_all(tasklet_product_model) == ["research/README.md"]  # index is stale
    found = validators.run(tasklet_product_model)
    assert [(f.code, f.severity) for f in found] == [("NO_SYSTEM_STEPS", "warn")]
    body = p.read_text()
    head, tail = body.split("## Engineering requirements surfaced", 1)
    rest = tail.split("\n## ", 1)
    p.write_text(head + "## Engineering requirements surfaced\n\nnone\n\n## " + rest[1])
    assert "NO_SYSTEM_STEPS" not in codes(tasklet_product_model)


def test_confirmed_needs_tier_two_evidence_on_half_the_observed_steps(
    tasklet_product_model: Path,
) -> None:
    from pflib.index import WorkspaceIndex

    index = WorkspaceIndex(tasklet_product_model)
    steps, _ = workflows.parse_steps((tasklet_product_model / FLOW).read_text())
    weak = [rec.id for _, rec in index.records("S") if rec.get("Tier").strip() in {"3", "4"}]
    assert weak, "fixture needs a tier 3-4 source"
    for s in steps:
        if s.tag == "observed":
            edit(tasklet_product_model, s.line, s.line.split(" — ")[0] + " — " + weak[0])
    assert "WORKFLOW_CONFIDENCE" in codes(tasklet_product_model)
    edit(tasklet_product_model, "- Confidence: CONFIRMED", "- Confidence: PROBABLE")
    assert "WORKFLOW_CONFIDENCE" not in codes(tasklet_product_model)
