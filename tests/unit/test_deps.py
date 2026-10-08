from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from conftest import TASKLET

from pflib import config, deps, state, workspace
from pflib.errors import PFError

SCOUT = {"contributor-scout@phantom-in": [{"version": "1.2.0", "installPath": "/x"}]}


@pytest.fixture
def home(tmp_path: Path) -> Path:
    h = tmp_path / "home"
    (h / ".claude/plugins").mkdir(parents=True)
    return h


@pytest.fixture
def ws(tasklet_discovery: Path) -> Path:
    config.write_config(tasklet_discovery, {"capabilities.claude_bin": "definitely-not-claude"})
    return tasklet_discovery


def test_check_records_resolution_in_state(ws: Path, home: Path) -> None:
    result = deps.check(ws, {"deep-research"}, home)
    assert result["capabilities"]["research.deep"]["provider"] == "anthropic-skills:deep-research"
    assert result["offer"] == ["repo.intel"]
    resolved = state.load(ws).capabilities["resolved"]
    assert (
        resolved["repo.intel"]["provider"] == "builtin" and resolved["research.deep"]["resolved_at"]
    )
    deps.mark_offered(ws, ["repo.intel"])
    assert deps.check(ws, {"deep-research"}, home)["offer"] == []


def test_check_without_workspace_writes_nothing(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pflib import capabilities

    monkeypatch.setattr(capabilities, "claude_plugin_list", lambda claude_bin: None)  # no real CLI
    result = deps.check(None, set(), home)
    assert result["workspace"] is None and "repo.intel" in result["offer"]


def test_install_without_confirmation_runs_nothing(
    ws: Path, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*a: object, **k: object) -> None:
        raise AssertionError("subprocess must not run without --confirmed")

    monkeypatch.setattr(subprocess, "run", forbidden)
    payload, code = deps.install(ws, "repo.intel", None, False, False, home)
    assert code == 0 and payload["executed"] is False and payload["results"] == []
    assert payload["commands"][-1] == [
        "definitely-not-claude",
        "plugin",
        "install",
        "contributor-scout@phantom-in",
        "--scope",
        "project",
    ]
    assert "ask the user" in payload["message"]
    assert "deps-install" not in [e["event"] for e in workspace.read_history(ws)]


def test_confirmed_install_runs_exact_argv_in_order(
    ws: Path, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        assert kw["cwd"] == str(ws) and "shell" not in kw
        return subprocess.CompletedProcess(argv, 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    payload, code = deps.install(ws, "repo.intel", "user", True, False, home)
    assert code == 0 and payload["executed"] and calls == payload["commands"]
    assert calls[-1][-2:] == ["--scope", "user"]
    assert "new Claude Code session" in payload["message"]
    event = workspace.read_history(ws)[-1]
    assert event["event"] == "deps-install" and event["exit"] == 0


def test_failed_install_stops_and_reports(ws: Path, home: Path,
                                          monkeypatch: pytest.MonkeyPatch) -> None:  # fmt: skip
    monkeypatch.setattr(subprocess, "run", lambda argv, **kw: subprocess.CompletedProcess(
        argv, 1, "", "boom"))  # fmt: skip
    payload, code = deps.install(ws, "repo.intel", None, True, False, home)
    assert code == 1 and len(payload["results"]) == 1 and payload["results"][0]["stderr"] == "boom"


def test_bad_scope(ws: Path, home: Path) -> None:
    with pytest.raises(PFError) as info:
        deps.install(ws, "repo.intel", "galaxy", False, False, home)
    assert info.value.code == "CAP_BAD_SCOPE"


def test_use_pins_and_validates(ws: Path) -> None:
    assert deps.use(ws, "research.deep", "builtin") == {"pins": {"research.deep": "builtin"}}
    stored = json.loads((ws / ".productforge/config.json").read_text())
    assert stored["capabilities.pins"] == {"research.deep": "builtin"}
    with pytest.raises(PFError) as info:
        deps.use(ws, "research.deep", "graphify")
    assert info.value.code == "CAP_UNKNOWN"
    with pytest.raises(PFError):
        deps.mark_offered(ws, ["teleport"])


def test_fixture_state_without_capabilities_still_loads() -> None:
    assert state.load(TASKLET / "DISCOVERY").capabilities == {}
