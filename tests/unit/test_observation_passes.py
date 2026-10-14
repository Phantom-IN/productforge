"""Observation-pass output through staging and merge (v2 phase 04): screen-level workflow steps,
a 403 settling a permission cell, and API-shape inferences that never state internals."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pflib import brief, domain, merge, observe, validators, workspace
from pflib.errors import UsageError
from pflib.index import WorkspaceIndex

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "observe-session"
SID = "obs-20261014-140548"


@pytest.fixture
def ws(tasklet_product_model: Path) -> Path:
    shutil.copytree(FIXTURE / SID, observe.observe_root(tasklet_product_model) / SID)
    observe.ingest(tasklet_product_model, SID)
    return tasklet_product_model


def ob(ws: Path, title_start: str) -> str:
    return next(
        r.id for _, r in WorkspaceIndex(ws).records("OB") if r.title.startswith(title_start)
    )


def stage(ws: Path, role: str, files: dict[str, str]) -> str:
    run_id, path = workspace.create_staging_run(ws, role)
    for rel, text in files.items():
        (path / rel).parent.mkdir(parents=True, exist_ok=True)
        (path / rel).write_text(text)
    return run_id


def errors(ws: Path) -> list[validators.Finding]:
    return [f for f in validators.run(ws) if f.severity == "error"]


def test_workflow_steps_cite_observations(ws: Path) -> None:
    submit = ob(ws, "Submit form “New task”")
    screen = ob(ws, "Screen `/tasks`")
    create = ob(ws, "Endpoint `POST /api/tasks`")
    steps = (
        "### REVISE W-001\n- Why: an observe session recorded the flow screen by screen\n\n"
        "## Steps\n\n"
        f"1. [observed] Member opens the task list on /tasks — {screen}\n"
        f"2. [observed] Member fills Title and an optional Due date, submits New task — {submit}\n"
        f"3. [implied-system] Persist the task and return it with its id — {create}, F-001\n"
        f"4. [observed] The new task appears in the list — {screen}\n"
    )
    report = merge.merge(ws, stage(ws, "ux-analyst", {"research/workflows/w.md": steps}))
    assert report.revised == ["W-001"]
    assert errors(ws) == []


def test_a_403_settles_a_permission_cell(ws: Path) -> None:
    denied = ob(ws, "Permission `GET /api/settings` → 403")
    before = {g["rule"] for g in domain.permission_gaps(WorkspaceIndex(ws))}
    assert "PR-002" in before
    text = (
        "### PR-?1 — Create membership (observed)\n- Resource: E-03\n- Action: create\n"
        "- Grants: RL-01 ✓, RL-02 ✓, RL-03 ✗, RL-04 ✗\n- Limited means:\n"
        f"- Evidence: D-026, {denied}\n- Confidence: PROBABLE\n\n"
        "### AMEND PR-002\n- Status: superseded-by PR-?1\n"
        "- Why: a member's session was refused (403) for the owner-only action\n"
    )
    merge.merge(ws, stage(ws, "domain-architect", {"spec/PERMISSIONS_MATRIX.md": text}))
    after = {g["rule"] for g in domain.permission_gaps(WorkspaceIndex(ws))}
    assert "PR-002" not in after and len(after) == len(before) - 1
    assert errors(ws) == []


def inference(ws: Path, target: str) -> list[str]:
    realtime = ob(ws, "Realtime `/ws`")
    files = {
        "research/DISCOVERY_LEDGER.md": (
            "### D-?1 — The task list receives task.created messages over a socket\n"
            "- Claim: After a task is created the open list gets a task.created message on /ws.\n"
            f"- Evidence: {realtime}\n- Confidence: CONFIRMED\n- Product impact: live lists\n"
            "- Engineering impact: a push channel per workspace\n- Status: active\n"
        ),
        "research/architecture-inference.md": (
            "### A-?1 — New tasks reach open lists live\n- Area: realtime\n"
            "- Observation: An open task list shows a new task without a reload\n"
            "- Evidence: D-?1\n- Confidence: CONFIRMED\n"
            "- Engineering implication: The server pushes task events to open clients\n"
            f"- Target implementation: {target}\n"
            "- Our requirement: New tasks must reach open lists within 2 s\n"
            "- Derived from: W-001, D-?1\n"
        ),
    }
    merge.merge(ws, stage(ws, "systems-architect", files))
    return [f.code for f in errors(ws)]


def test_observed_api_shapes_may_be_stated(ws: Path) -> None:
    assert inference(ws, "WebSocket /ws pushes {type, task: {id, title, due}} messages") == []


def test_internals_from_observations_are_refused(ws: Path) -> None:
    assert inference(ws, "Postgres LISTEN/NOTIFY fanned out over Redis") == [
        "INTERNALS_FROM_OBSERVATION"
    ]


def test_briefs_take_the_summary_never_raw_session_files(ws: Path) -> None:
    raw = f".productforge/observe/{SID}/events.jsonl"
    with pytest.raises(UsageError) as exc:
        brief.render(ws, "ux-analyst", "Observation pass", inputs=[raw])
    assert exc.value.code == "BRIEF_RAW_SESSION"
    ok = brief.render(ws, "ux-analyst", "Observation pass",
                      inputs=[f".productforge/observe/{SID}/summary.json"])  # fmt: skip
    assert "summary.json" in ok.text
