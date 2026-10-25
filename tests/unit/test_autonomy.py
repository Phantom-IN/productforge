from __future__ import annotations

import json
from pathlib import Path

from conftest import copy_snapshot
from test_prompt_contracts import REFERENCES, SKILL, check_skill, commands_text
from test_stage_guard import denied, payload, run

from pflib import autonomy, config, state, workspace


def pf(pf_cli, *args: str, ws: Path) -> tuple[int, dict]:  # type: ignore[no-untyped-def,type-arg]
    code, out, err = pf_cli(*args, "--workspace", str(ws), "--json")
    return code, json.loads(out or err or "{}")


def grant(pf_cli, ws: Path) -> None:  # type: ignore[no-untyped-def]
    hash_ = autonomy.current_hash(ws)
    assert pf(pf_cli, "autonomy", "grant", "--confirmed", "--text-sha256", hash_, ws=ws)[0] == 0


def test_grant_needs_confirmed_and_the_current_hash(pf_cli, tasklet_discovery: Path) -> None:  # type: ignore[no-untyped-def]
    ws = tasklet_discovery
    HASH = autonomy.current_hash(ws)
    code, out = pf(pf_cli, "autonomy", "grant", "--text-sha256", HASH, ws=ws)
    assert code == 2 and out["error"] == "AUTONOMY_NOT_CONFIRMED"
    code, out = pf(pf_cli, "autonomy", "grant", "--confirmed", "--text-sha256", "0" * 64, ws=ws)
    assert code == 2 and out["error"] == "AUTONOMY_TEXT_CHANGED"
    assert pf(pf_cli, "autonomy", "grant", "--confirmed", ws=ws)[0] == 2
    assert not autonomy.active(state.load(ws), ws)


def test_grant_show_revoke_cycle_is_logged(pf_cli, tasklet_discovery: Path) -> None:  # type: ignore[no-untyped-def]
    ws = tasklet_discovery
    HASH = autonomy.current_hash(ws)
    _, out = pf(pf_cli, "autonomy", "show", ws=ws)
    assert (
        out["active"] is False
        and out["text_sha256"] == HASH
        and out["text"] == autonomy.text(ws)
        and "competitors" in out["text"]
    )
    grant(pf_cli, ws)
    st = state.load(ws)
    assert autonomy.active(st, ws) and st.autonomy["text_sha256"] == HASH
    assert pf(pf_cli, "autonomy", "revoke", ws=ws)[1]["active"] is False
    assert not state.load(ws).autonomy
    events = [e["event"] for e in workspace.read_history(ws)]
    assert events == ["autonomy-grant", "autonomy-revoke"]


def test_a_grant_for_changed_text_is_not_active(tasklet_discovery: Path) -> None:
    ws = tasklet_discovery
    st = state.WorkspaceState(product={})
    autonomy.grant(st, "2026-01-01T00:00:00Z", ws)
    assert autonomy.active(st, ws)
    st.autonomy["text_sha256"] = "stale"
    assert not autonomy.active(st, ws)


def test_the_consent_text_names_the_effective_permission_args_and_binary(
    tasklet_discovery: Path,
) -> None:
    ws = tasklet_discovery
    before = autonomy.current_hash(ws)
    assert "--dangerously-skip-permissions" in autonomy.text(ws) and "`claude`" in autonomy.text(ws)
    st = state.load(ws)
    autonomy.grant(st, "2026-01-01T00:00:00Z", ws)
    assert autonomy.active(st, ws)
    config.write_config(ws, {"auto.permission_args": ["--permission-mode", "auto"]})
    assert "--permission-mode auto" in autonomy.text(ws)
    assert autonomy.current_hash(ws) != before and not autonomy.active(st, ws)
    config.write_config(ws, {"capabilities.claude_bin": "/opt/claude"})
    assert "`/opt/claude`" in autonomy.text(ws)


def test_revoke_without_a_grant_saves_and_logs_nothing(tasklet_discovery: Path) -> None:
    ws = tasklet_discovery
    mtime = state.state_path(ws).stat().st_mtime_ns
    out = autonomy.do_revoke(ws)
    assert out["active"] is False and state.state_path(ws).stat().st_mtime_ns == mtime
    assert not [e for e in workspace.read_history(ws) if e["event"] == "autonomy-revoke"]
    assert autonomy.revoke(state.load(ws)) is False


def test_unparsable_decision_lines_are_skipped(tasklet_discovery: Path) -> None:
    ws = tasklet_discovery
    autonomy.decide(ws, "q", "c", "w")
    with open(autonomy.decisions_path(ws), "a", encoding="utf-8") as handle:
        handle.write("{torn line\n[1, 2]\n")
    autonomy.decide(ws, "q2", "c2", "w2")
    assert [r["question"] for r in autonomy.read_decisions(ws)] == ["q", "q2"]
    assert autonomy.count_decisions(ws) == 2


def test_state_roundtrip_and_validation(tasklet_discovery: Path) -> None:
    data = json.loads(state.state_path(tasklet_discovery).read_text())
    assert "autonomy" not in data and state.validate_dict(data) == []
    data["autonomy"] = {"granted_at": "x", "text_sha256": "y"}
    assert state.validate_dict(data) == []
    assert state.WorkspaceState.from_dict(data).to_dict()["autonomy"] == data["autonomy"]
    data["autonomy"] = {"granted_at": 1}
    assert state.validate_dict(data)


def test_auto_advance_is_refused_without_a_grant(pf_cli, tasklet_discovery: Path) -> None:  # type: ignore[no-untyped-def]
    ws = tasklet_discovery
    code, out = pf(pf_cli, "advance", "--to", "PRODUCT_MODEL", "--auto", ws=ws)
    assert code == 2 and out["error"] == "AUTONOMY_NOT_GRANTED"
    assert state.load(ws).state is state.State.DISCOVERY
    code, out = pf(pf_cli, "complete", "--auto", ws=ws)
    assert code == 2 and out["error"] == "AUTONOMY_NOT_GRANTED"


def test_auto_advance_with_a_failing_gate_does_not_move(pf_cli, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    ws = copy_snapshot("DISCOVERY_FAILING", tmp_path / "ws")
    grant(pf_cli, ws)
    code, out = pf(pf_cli, "advance", "--to", "PRODUCT_MODEL", "--auto", ws=ws)
    assert code == 1 and out["transitioned"] is False
    assert state.load(ws).state is state.State.DISCOVERY


def test_auto_advance_with_a_passing_gate_moves_one_stage_and_logs(
    pf_cli,  # type: ignore[no-untyped-def]
    tasklet_discovery: Path,
) -> None:
    ws = tasklet_discovery
    grant(pf_cli, ws)
    code, out = pf(pf_cli, "advance", "--to", "PRODUCT_MODEL", "--auto", ws=ws)
    assert code == 0 and out["transitioned"] is True
    assert state.load(ws).state is state.State.PRODUCT_MODEL
    last = workspace.read_history(ws)[-1]
    assert last["event"] == "auto-advance" and last["to"] == "PRODUCT_MODEL"
    # revoking ends it
    pf(pf_cli, "autonomy", "revoke", ws=ws)
    assert pf(pf_cli, "advance", "--to", "SCOPE_DEFINED", "--auto", ws=ws)[0] == 2


def test_auto_complete_is_logged(pf_cli, tasklet_plan: Path) -> None:  # type: ignore[no-untyped-def]
    ws = tasklet_plan
    grant(pf_cli, ws)
    code, out = pf(pf_cli, "complete", "--auto", ws=ws)
    assert code == 0 and out["completed"] is True
    assert workspace.read_history(ws)[-1]["event"] == "auto-complete"


def test_without_a_grant_confirmed_still_works(pf_cli, tasklet_discovery: Path) -> None:  # type: ignore[no-untyped-def]
    code, out = pf(pf_cli, "advance", "--to", "PRODUCT_MODEL", "--confirmed", ws=tasklet_discovery)
    assert code == 0 and out["transitioned"] is True


def test_decisions_append_and_list(pf_cli, tasklet_discovery: Path) -> None:  # type: ignore[no-untyped-def]
    ws = tasklet_discovery
    assert pf(pf_cli, "decide", "--list", ws=ws)[1]["count"] == 0
    args = ("decide", "--question", "Domain split?", "--choice", "Use these domains")
    code, out = pf(pf_cli, *args, "--why", "Recommended", "--command", "features", ws=ws)
    assert code == 0 and out["decisions"] == 1
    pf(pf_cli, *args, "--why", "Recommended", ws=ws)
    rows = pf(pf_cli, "decide", "--list", ws=ws)[1]["decisions"]
    assert [r["choice"] for r in rows] == ["Use these domains"] * 2
    assert rows[0]["command"] == "features" and rows[0]["stage"] == "DISCOVERY"
    assert pf(pf_cli, "decide", "--question", "q", ws=ws)[0] == 2
    assert (ws / ".productforge/decisions.jsonl").read_text().count("\n") == 2


def test_status_reports_autonomy_and_decisions(pf_cli, tasklet_discovery: Path) -> None:  # type: ignore[no-untyped-def]
    ws = tasklet_discovery
    _, out = pf(pf_cli, "status", ws=ws)
    assert out["autonomy"] == {"active": False, "granted_at": None} and out["decisions"] == 0
    grant(pf_cli, ws)
    pf(pf_cli, "decide", "--question", "q", "--choice", "c", "--why", "w", ws=ws)
    _, out = pf(pf_cli, "status", ws=ws)
    assert out["autonomy"]["active"] is True and out["autonomy"]["granted_at"]
    assert out["decisions"] == 1
    code, text, _ = pf_cli("status", "--workspace", str(ws))
    assert "Autonomy: active" in text and "1 decision(s)" in text


def test_the_guard_denies_agent_writes_to_the_decisions_log(tasklet_discovery: Path) -> None:
    _, out, _ = run(payload("write", tasklet_discovery, ".productforge/decisions.jsonl"))
    assert denied(out) is not None


def test_skill_autonomous_section_contract() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert check_skill(text) == []
    section = text.split("## Autonomous mode", 1)[1].split("\n## ", 1)[0]
    for needle in (
        "autonomy.active",
        "advance --to <target_stage> --auto",
        "one transition per invocation",
        "Recommended",
        "Use these domains",
        "pf.py decide",
        "deps use <capability> builtin",
        "`competitors` always runs before `scope`",
        "Observe",
        "configured maximum",
        "decisions made",
        "references/commands-auto.md",
    ):
        assert needle in section, needle
    assert "Never grant it yourself" in section
    detail = (REFERENCES / "commands-auto.md").read_text(encoding="utf-8")
    assert "complete --auto" in detail
    assert "always runs before `scope`" in detail and "AUTONOMY_NOT_GRANTED" in detail
    assert "Autonomous mode" in commands_text()


def test_golden_rule_wording_mentions_the_grant() -> None:
    root = Path(__file__).resolve().parents[2]
    for rel in ("CLAUDE.md", "skills/productforge/references/stage-gates.md"):
        assert "autonomy grant" in (root / rel).read_text(encoding="utf-8"), rel
