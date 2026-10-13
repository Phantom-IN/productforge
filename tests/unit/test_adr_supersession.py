from __future__ import annotations

import json
from pathlib import Path

from pflib import merge, records, render, validators, workspace


def stage(ws: Path, files: dict[str, str]) -> str:
    run_id, path = workspace.create_staging_run(ws, "systems-architect")
    for rel, text in files.items():
        (path / rel).parent.mkdir(parents=True, exist_ok=True)
        (path / rel).write_text(text)
    return run_id


def test_changing_a_decision_supersedes_and_repoints(tasklet_arch: Path) -> None:
    ws = tasklet_arch
    new_adr = (
        "### ADR-?1 — Server-sent events for board changes\n- Topic: realtime\n"
        "- Context: The user wants changes within 2 s (R-002, A-001)\n"
        "- Decision: The API streams board changes over server-sent events\n"
        "- Alternatives: polling every 30 s; WebSockets; a hosted realtime service\n"
        "- Reason: One-way updates are enough; SSE runs over plain HTTP\n"
        "- Trade-offs: Long-lived connections per open board\n- Satisfies: R-002, A-001\n"
        "- Status: accepted\n"
    )
    amend = (
        "### AMEND ADR-006\n- Status: superseded-by ADR-?1\n"
        "- Why: the user asked for faster updates\n"
    )
    repoint = (
        "### AMEND AP-001\n- Decision: ADR-?1\n"
        "- Proposed implementation: Server-sent events per board\n"
        "- Why: ADR-006 was superseded\n"
    )
    report = merge.merge(ws, stage(ws, {
        "spec/decisions/sse.md": new_adr + "\n" + amend,
        "research/architecture-inference.md": repoint,
    }))  # fmt: skip
    new_id = report.id_map["ADR-?1"]
    assert new_id == "ADR-012" and sorted(report.amended) == ["ADR-006", "AP-001"]
    assert (ws / "spec/decisions/ADR-012-server-sent-events-for-board-changes.md").is_file()
    old = next((ws / "spec/decisions").glob("ADR-006-*.md")).read_text()
    assert "- Status: superseded-by ADR-012" in old  # history is kept
    assert validators.run(ws) == []
    decisions = render.regions((ws / "spec/ARCHITECTURE.md").read_text())["decisions"]
    assert (
        "| ADR-006 | Polling instead of push in V1 | realtime | superseded-by ADR-012 |"
        in decisions
    )
    ap = records.parse_document((ws / "research/architecture-inference.md").read_text()).record(
        "AP-001"
    )
    assert ap is not None and ap.get("Decision") == "ADR-012"


def test_set_preferences(pf_cli, tasklet_scope: Path) -> None:  # type: ignore[no-untyped-def]
    ws = str(tasklet_scope)
    code, out, _ = pf_cli("set-preferences", "--stack", "Next.js, PostgreSQL ,", "--deployment",
                          "serverless", "--workspace", ws, "--json")  # fmt: skip
    assert code == 0
    assert json.loads(out)["architecture"] == {"preferences": ["Next.js", "PostgreSQL"],
                                               "deployment_target": "serverless"}  # fmt: skip
    code, out, _ = pf_cli("set-preferences", "--workspace", ws, "--json")  # report only
    assert json.loads(out)["architecture"]["preferences"] == ["Next.js", "PostgreSQL"]
