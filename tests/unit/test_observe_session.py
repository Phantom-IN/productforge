"""pf.py observe start · status · stop with a stand-in recorder (no Playwright needed)."""

from __future__ import annotations

import json
import os
import signal
import sys
from pathlib import Path

import pytest

from pflib import observe, state
from pflib.errors import CheckFailed, UsageError

FAKE = Path(__file__).resolve().parents[1] / "observe" / "fake_recorder.py"


@pytest.fixture
def ws(tasklet_discovery: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    observe.record_consent(tasklet_discovery, confirmed=True)
    monkeypatch.setattr(observe, "recorder_python", lambda home=None: Path(sys.executable))
    monkeypatch.setattr(observe, "recorder_command",
                        lambda py, folder, headless=False: [str(py), str(FAKE), "--session-dir",
                                                            str(folder)])  # fmt: skip
    return tasklet_discovery


def test_start_status_stop(ws: Path) -> None:
    out = observe.start(ws, label="Create a board")
    sid = out["session"]
    assert observe.SESSION_RE.match(sid) and out["panel_url"].startswith("http://127.0.0.1:")
    meta = json.loads((observe.observe_root(ws) / sid / "session.json").read_text())
    assert meta["url"] == state.load(ws).product["target_url"]
    assert meta["config"]["allowed_hosts"] == ["tasklet.example"]
    assert meta["label"] == "Create a board" and meta["consent_sha256"] == observe.consent_hash()
    assert observe.session_status(ws)["status"] == "recording"
    with pytest.raises(UsageError) as exc:
        observe.start(ws)
    assert exc.value.code == "OBSERVE_ACTIVE"
    done = observe.stop(ws)
    assert done["status"] == "stopped" and done["panel_url"] is None
    events = [h["event"] for h in __import__("pflib").workspace.read_history(ws)]
    assert "observe-start" in events and "observe-stop" in events


def test_a_dead_recorder_reads_as_crashed(ws: Path) -> None:
    out = observe.start(ws)
    os.kill(out["pid"], signal.SIGKILL)
    for _ in range(50):
        if observe.session_status(ws)["status"] == "crashed":
            break
        __import__("time").sleep(0.05)
    assert observe.session_status(ws)["status"] == "crashed"
    assert observe.active_session(ws) is None


def test_stop_falls_back_to_a_signal(ws: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PF_FAKE_RECORDER_IGNORE_STOP", "1")
    observe.start(ws)
    assert observe.stop(ws, timeout=0.5)["status"] == "crashed"  # killed, never wrote "stopped"


def test_a_failed_start_reports_the_recorder_output(
    ws: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PF_FAKE_RECORDER_FAIL", "1")
    with pytest.raises(CheckFailed) as exc:
        observe.start(ws)
    assert exc.value.code == "OBSERVE_START_FAILED" and "playwright exploded" in str(exc.value)


def test_start_needs_consent_install_and_stage(
    tasklet_discovery: Path, tasklet_scope: Path, tmp_path: Path
) -> None:
    with pytest.raises(UsageError) as exc:
        observe.start(tasklet_discovery)
    assert exc.value.code == "OBSERVE_NO_CONSENT"
    observe.record_consent(tasklet_discovery, confirmed=True)
    with pytest.raises(UsageError) as exc:
        observe.start(tasklet_discovery, home=tmp_path)
    assert exc.value.code == "OBSERVE_NOT_INSTALLED"
    observe.record_consent(tasklet_scope, confirmed=True)
    with pytest.raises(UsageError) as exc:
        observe.start(tasklet_scope)
    assert exc.value.code == "OBSERVE_WRONG_STAGE"


def test_status_without_sessions(tasklet_discovery: Path) -> None:
    with pytest.raises(UsageError) as exc:
        observe.session_status(tasklet_discovery)
    assert exc.value.code == "OBSERVE_NO_SESSION"
    with pytest.raises(UsageError):
        observe.session_status(tasklet_discovery, "../../etc")


def test_only_our_temporary_profile_is_removed(ws: Path, tmp_path: Path) -> None:
    import tempfile

    sid = observe.start(ws)["session"]
    observe.stop(ws)
    folder = observe.observe_root(ws) / sid
    ours = Path(tempfile.mkdtemp(prefix=observe.PROFILE_PREFIX))
    other = tmp_path / "keep-me"
    other.mkdir()
    for profile, survives in ((other, True), (ours, False)):
        (folder / "status.json").write_text(json.dumps({"status": "stopped",
                                                        "profile_dir": str(profile)}))  # fmt: skip
        observe.stop(ws, sid)
        assert profile.exists() is survives


def test_discard_deletes_raw_files_and_logs_the_reason(ws: Path) -> None:
    sid = observe.start(ws)["session"]
    with pytest.raises(UsageError) as exc:
        observe.discard(ws, sid, "oops")
    assert exc.value.code == "OBSERVE_ACTIVE"
    observe.stop(ws)
    with pytest.raises(UsageError) as exc:
        observe.discard(ws, sid, " ")
    assert exc.value.code == "OBSERVE_NO_REASON"
    out = observe.discard(ws, sid, "recorded the wrong account")
    assert out["discarded"] and not (observe.observe_root(ws) / sid).exists()
    last = __import__("pflib").workspace.read_history(ws)[-1]
    assert last["event"] == "observe-discard" and last["reason"] == "recorded the wrong account"


def test_old_sessions_are_pruned_on_start(ws: Path) -> None:
    from datetime import timedelta

    from pflib import config, workspace

    old = observe.start(ws)["session"]
    observe.stop(ws)
    meta_path = observe.observe_root(ws) / old / "session.json"
    meta = json.loads(meta_path.read_text())
    meta["started_at"] = workspace.iso(workspace.utc_now() - timedelta(days=31))
    meta_path.write_text(json.dumps(meta))
    config.write_config(ws, {"observe.retain_days": 0})
    assert observe.prune(ws) == []
    config.write_config(ws, {"observe.retain_days": 30})
    out = observe.start(ws)
    assert out["pruned"] == [old] and observe.sessions(ws) == [out["session"]]
    observe.stop(ws)


def test_bad_screenshot_mode_is_refused(ws: Path) -> None:
    from pflib import config

    config.write_config(ws, {"observe.screenshots": "sometimes"})
    with pytest.raises(UsageError) as exc:
        observe.start(ws)
    assert exc.value.code == "OBSERVE_BAD_CONFIG"
