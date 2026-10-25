from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
from conftest import SCRIPTS_DIR, TASKLET, copy_snapshot

import pf
from pflib import auto, autonomy, config, state, workspace

STAGE_SNAPSHOT = {
    "DISCOVERY": "DISCOVERY",
    "PRODUCT_MODEL": "PRODUCT_MODEL",
    "SCOPE_DEFINED": "SCOPE_DEFINED",
    "ARCHITECTURE_LOCKED": "ARCHITECTURE_LOCKED",
    "PHASE_PLAN_READY": "PHASE_PLAN_READY",
}


class FakeRunner:
    """Stands in for ``subprocess.run``: records every call, optionally 'does the work'."""

    def __init__(self, ws: Path, produce: bool = False, rc: int = 0) -> None:
        self.ws, self.produce, self.rc = ws, produce, rc
        self.calls: list[dict[str, Any]] = []

    def __call__(self, argv: list[str], **kw: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append({"argv": argv, **kw})
        if self.produce and self.rc == 0:
            stage = state.load(self.ws).state.value
            src = TASKLET / STAGE_SNAPSHOT[stage]
            for path in src.rglob("*"):
                rel = path.relative_to(src)
                if path.is_file() and rel.parts[0] != workspace.PF_DIR:
                    (self.ws / rel).parent.mkdir(parents=True, exist_ok=True)
                    (self.ws / rel).write_bytes(path.read_bytes())
        return subprocess.CompletedProcess(argv, self.rc)


class FakeSleep:
    def __init__(self) -> None:
        self.waits: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)


def setup(tmp_path: Path, snapshot: str, **cfg_over: Any) -> tuple[Path, dict[str, Any]]:
    ws = copy_snapshot(snapshot, tmp_path / "ws")
    st = state.load(ws)
    autonomy.grant(st, "2026-01-01T00:00:00Z", ws)
    state.save(ws, st)
    cfg = auto.load_cfg(ws)
    cfg.update(cfg_over)
    return ws, cfg


def events(ws: Path) -> list[str]:
    return [e["event"] for e in auto.read_log(ws)]


def test_scripted_tasklet_runs_to_completion(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING")
    runner, sleep = FakeRunner(ws, produce=True), FakeSleep()
    summary = auto.run(ws, cfg, pf._inproc(ws), runner, sleep)
    assert summary["completed"] is True and summary["stopped"] is None
    assert summary["stages_passed"] == [
        "DISCOVERY",
        "PRODUCT_MODEL",
        "SCOPE_DEFINED",
        "ARCHITECTURE_LOCKED",
    ]
    assert summary["sessions"] == len(runner.calls) == 5 and not sleep.waits
    hist = [e for e in workspace.read_history(ws) if e["event"].startswith("auto-")]
    assert [e["event"] for e in hist] == ["auto-advance"] * 4 + ["auto-complete"]
    assert events(ws).count("auto-advance") == 4 and "auto-complete" in events(ws)
    assert state.load(ws).state is state.State.PHASE_PLAN_READY
    assert "completed_at" in json.dumps(state.load(ws).to_dict())
    assert "ORCHESTRATOR_PROMPT.md" in summary["next_step"]


def test_a_stall_stops_after_two_unchanged_sessions(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING")
    runner = FakeRunner(ws)
    summary = auto.run(ws, cfg, pf._inproc(ws), runner, FakeSleep())
    assert len(runner.calls) == 2 and summary["stalls"] == 2
    assert summary["stopped"].startswith("stalled") and not summary["completed"]
    assert events(ws)[-2:] == ["stall", "stop"]


def test_failed_sessions_retry_then_stop(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING", max_retries=2, retry_wait_seconds=7)
    runner, sleep = FakeRunner(ws, rc=1), FakeSleep()
    summary = auto.run(ws, cfg, pf._inproc(ws), runner, sleep)
    assert sleep.waits == [7.0, 7.0] and len(runner.calls) == 3
    assert summary["retries"] == 3 and "retry limit" in summary["stopped"]
    assert [e["rc"] for e in auto.read_log(ws) if e["event"] == "retry"] == [1, 1, 1]


def test_max_sessions_stops_the_run(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING", max_sessions=1, max_stalls=9)
    runner = FakeRunner(ws)
    summary = auto.run(ws, cfg, pf._inproc(ws), runner, FakeSleep())
    assert len(runner.calls) == 1 and "session limit" in summary["stopped"]


def test_needs_transition_advances_with_auto(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY", max_sessions=0)
    runner = FakeRunner(ws)
    summary = auto.run(ws, cfg, pf._inproc(ws), runner, FakeSleep())
    assert not runner.calls and summary["stages_passed"] == ["DISCOVERY"]
    assert state.load(ws).state is state.State.PRODUCT_MODEL
    assert workspace.read_history(ws)[-1]["event"] == "auto-advance"


def test_a_failing_advance_or_missing_grant_stops(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY")
    st = state.load(ws)
    autonomy.revoke(st)
    state.save(ws, st)
    summary = auto.run(ws, cfg, pf._inproc(ws), FakeRunner(ws), FakeSleep())
    assert "refused" in summary["stopped"]
    assert state.load(ws).state is state.State.DISCOVERY


def test_the_stop_file_ends_the_run_between_sessions(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING", max_stalls=9)

    class Stopper(FakeRunner):
        def __call__(self, argv: list[str], **kw: Any) -> subprocess.CompletedProcess[str]:
            auto.request_stop(self.ws)
            return super().__call__(argv, **kw)

    runner = Stopper(ws)
    summary = auto.run(ws, cfg, pf._inproc(ws), runner, FakeSleep())
    assert len(runner.calls) == 1 and "stop file" in summary["stopped"]
    # a fresh start clears the flag and resumes
    runner2 = FakeRunner(ws)
    auto.run(ws, {**cfg, "max_stalls": 1}, pf._inproc(ws), runner2, FakeSleep())
    assert len(runner2.calls) == 1 and not auto.stop_path(ws).exists()


def test_a_missing_claude_binary_stops_without_retries(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING")
    sleep = FakeSleep()

    def missing(argv: list[str], **kw: Any) -> None:
        raise FileNotFoundError(argv[0])

    summary = auto.run(ws, cfg, pf._inproc(ws), missing, sleep)
    assert "not found" in summary["stopped"] and not sleep.waits


def test_budget_raise_respects_the_ceiling(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING", max_sources_ceiling=100)
    base = int(config.resolve("research.max_sources", ws))
    assert auto.raise_budget(ws, {"budget_needed": 0}, cfg) is None
    assert auto.raise_budget(ws, {"budget_needed": 5}, cfg) == base + 5
    assert auto.raise_budget(ws, {"budget_needed": 500}, cfg) == 100
    assert auto.raise_budget(ws, {"budget_needed": 500}, cfg) is None  # at the ceiling
    assert config.resolve("research.max_sources", ws) == 100
    rows = autonomy.read_decisions(ws)
    assert len(rows) == 2 and rows[-1]["choice"].endswith("-> 100")


def test_budget_raise_happens_in_the_loop_and_is_logged(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING", max_stalls=1)
    real = pf._inproc(ws)

    def with_budget(argv: list[str]) -> tuple[int, dict[str, Any]]:
        return (0, {"budget_needed": 3}) if argv == ["research-plan"] else real(argv)

    auto.run(ws, cfg, with_budget, FakeRunner(ws), FakeSleep())
    assert "budget" in events(ws) and autonomy.count_decisions(ws) == 1


def test_parallelism_is_applied_for_the_run(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING", max_stalls=1)
    auto.run(ws, cfg, pf._inproc(ws), FakeRunner(ws), FakeSleep())
    assert config.resolve("agents.max_pending_runs", ws) == 6
    assert config.resolve("features.max_parallel_domains", ws) == 6


def test_command_line_and_env(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING", max_stalls=1)
    runner = FakeRunner(ws)
    auto.run(ws, cfg, pf._inproc(ws), runner, FakeSleep())
    call = runner.calls[0]
    argv = call["argv"]
    assert argv[:3] == ["claude", "-p", "/productforge research"]
    assert argv[argv.index("--plugin-dir") + 1] == str(auto.plugin_root())
    assert (auto.plugin_root() / ".claude-plugin" / "plugin.json").is_file()
    assert argv[argv.index("--model") + 1] == "opus"
    assert "--dangerously-skip-permissions" in argv
    assert call["env"]["CLAUDE_CODE_SUBAGENT_MODEL"] == "sonnet" and call["cwd"] == str(ws)


def test_architect_gets_the_stack_and_permission_args_are_configurable(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY")
    cfg.update(stack="Next.js, PostgreSQL", permission_args=["--permission-mode", "auto"])
    argv = auto.session_command(ws, "architect", cfg)
    assert argv[2] == '/productforge architect --stack "Next.js, PostgreSQL"'
    assert (
        argv[-2:] == ["--permission-mode", "auto"] and "--dangerously-skip-permissions" not in argv
    )
    assert "--stack" not in auto.session_command(ws, "scope", cfg)[2]


def test_fingerprint_changes_with_counts_and_gate() -> None:
    a = {"open_stage": "DISCOVERY", "counts": {"S": 1}, "gate_progress": {"done": 1, "total": 3}}
    b = {**a, "counts": {"S": 2}}
    c = {**a, "gate_progress": {"done": 2, "total": 3}}
    assert len({auto.fingerprint(a), auto.fingerprint(b), auto.fingerprint(c)}) == 3
    assert auto.fingerprint(a) == auto.fingerprint(dict(a))


def test_dry_run_changes_nothing(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING")
    before = {p: p.read_bytes() for p in ws.rglob("*") if p.is_file()}
    runner = FakeRunner(ws)
    summary = auto.run(ws, cfg, pf._inproc(ws), runner, FakeSleep(), dry_run=True)
    assert not runner.calls and summary["next_session"][:2] == ["claude", "-p"]
    assert {p: p.read_bytes() for p in ws.rglob("*") if p.is_file()} == before


def test_auto_start_without_confirmed_shows_consent_and_runs_nothing(
    pf_cli,
    tmp_path: Path,  # type: ignore[no-untyped-def]
) -> None:
    ws = copy_snapshot("DISCOVERY_FAILING", tmp_path / "ws")
    code, out, _ = pf_cli("auto", "start", "--workspace", str(ws))
    assert code == 2 and autonomy.text(ws) in out and "--confirmed" in out
    assert f"--text-sha256 {autonomy.current_hash(ws)}" in out
    assert not auto.log_path(ws).exists() and not state.load(ws).autonomy
    code, out, _ = pf_cli("auto", "start", "--workspace", str(ws), "--json")
    data = json.loads(out)
    assert code == 2 and data["text_sha256"] == autonomy.current_hash(ws)
    assert f"--text-sha256 {data['text_sha256']}" in data["command"]
    assert data["permission_args"] == ["--dangerously-skip-permissions"]


def test_auto_start_confirmed_grants_inits_and_drives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}

    def fake_run(ws: Path, cfg: dict[str, Any], call: Any, **kw: Any) -> dict[str, Any]:
        seen.update(ws=ws, cfg=cfg)
        return {"completed": True, "stopped": None, "sessions": 0, "retries": 0,
                "stages_passed": [], "decisions": 0, "next_step": "x"}  # fmt: skip

    monkeypatch.setattr(pf.auto, "run", fake_run)
    out = tmp_path / "newws"
    code = pf.main(
        ["auto", "start", "https://tasklet.example", "--out", str(out), "--scope", "tasks",
         "--stack", "Go", "--confirmed", "--text-sha256", autonomy.current_hash(None), "--json"]
    )  # fmt: skip
    assert code == 0 and seen["ws"] == out and seen["cfg"]["stack"] == "Go"
    assert autonomy.active(state.load(out), out)
    assert any(e["event"] == "autonomy-grant" for e in workspace.read_history(out))


def test_auto_status_and_stop(pf_cli, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    ws, cfg = setup(tmp_path, "DISCOVERY_FAILING", max_stalls=1)
    auto.run(ws, cfg, pf._inproc(ws), FakeRunner(ws), FakeSleep())
    code, out, _ = pf_cli("auto", "status", "--workspace", str(ws), "--json")
    data = json.loads(out)
    assert code == 0 and data["log"][-1]["event"] == "stop" and data["status"]["autonomy"]["active"]
    code, out, _ = pf_cli("auto", "stop", "--workspace", str(ws), "--json")
    assert code == 0 and auto.stop_path(ws).is_file()


def test_only_the_allowed_modules_start_processes() -> None:
    allowed = {"deps.py", "capabilities.py", "observe.py", "auto.py"}
    pattern = re.compile(r"^\s*(import subprocess|from subprocess import)", re.M)
    offenders = [
        p.name
        for p in [SCRIPTS_DIR / "pf.py", *sorted((SCRIPTS_DIR / "pflib").rglob("*.py"))]
        if pattern.search(p.read_text(encoding="utf-8")) and p.name not in allowed
    ]
    assert offenders == []
    source = (SCRIPTS_DIR / "pflib" / "auto.py").read_text(encoding="utf-8")
    assert "subprocess.run" in source and "Popen" not in source and "shell=True" not in source


def test_skill_auto_command_contract() -> None:
    from test_prompt_contracts import REFERENCES, SKILL, check_skill

    text = SKILL.read_text(encoding="utf-8")
    assert check_skill(text) == [] and text.count("\n") < 400
    assert "`auto <url> --scope" in text and "**`/productforge auto`** section" in text
    detail = (REFERENCES / "commands-auto.md").read_text(encoding="utf-8")
    section = detail.split("## The `auto` command", 1)[1]
    for needle in (
        "autonomy show",
        "AskUserQuestion",
        "Run autonomously (Recommended)",
        "autonomy grant --confirmed --text-sha256",
        "run_in_background",
        "auto start --workspace <ws>",
        "caffeinate -is",
        "auto status",
        "auto stop",
        "--plugin-dir",
        "auto.permission_args",
    ):
        assert needle in section, needle
    assert all(f"`{k}`" in (SCRIPTS_DIR.parents[2] / "docs/configuration.md").read_text()
               for k in config.DEFAULTS if k.startswith("auto."))  # fmt: skip


def test_workflow_cap_below_required_is_raised_and_logged(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "PRODUCT_MODEL", max_stalls=1)
    for p in (ws / "research" / "workflows").glob("*.md"):
        p.unlink()
    config.write_config(ws, {"model.max_workflows": 2})
    calls: list[list[str]] = []
    real = pf._inproc(ws)

    def spy(argv: list[str]) -> tuple[int, dict[str, Any]]:
        calls.append(argv)
        return real(argv)

    auto.run(ws, cfg, spy, FakeRunner(ws), FakeSleep())
    assert ["workflow-candidates"] in calls
    assert config.resolve("model.max_workflows", ws) == 5  # effective_cap: the 5 core domains
    raised = [e for e in auto.read_log(ws) if e["event"] == "config-raise"]
    assert [(e["key"], e["frm"], e["to"]) for e in raised] == [("model.max_workflows", 2, 5)]
    assert any("model.max_workflows 2 -> 5" in r["choice"] for r in autonomy.read_decisions(ws))
    assert any(e["event"] == "config-set" for e in workspace.read_history(ws))


def test_workflow_cap_raise_respects_the_ceiling(tmp_path: Path) -> None:
    ws, cfg = setup(tmp_path, "PRODUCT_MODEL", max_workflows_ceiling=4)
    config.write_config(ws, {"model.max_workflows": 2})
    payload = {"cap_below_required": 5, "effective_cap": 9}
    assert auto.raise_workflow_cap(ws, {"effective_cap": 9}, cfg) is None  # satisfiable
    assert auto.raise_workflow_cap(ws, payload, cfg) == 4
    assert auto.raise_workflow_cap(ws, payload, cfg) is None  # at the ceiling
    assert config.resolve("model.max_workflows", ws) == 4
