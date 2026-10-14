from __future__ import annotations

import json
from pathlib import Path

from pflib import capabilities, deps, observe, state

CAP = "browser.observe"


def resolution(home: Path) -> capabilities.Resolution:
    reg = capabilities.load_registry()
    detections = capabilities.detect(reg, set(), home=home, plugin_list=[])
    return capabilities.resolve(reg, detections)[CAP]


def fake_venv(home: Path, ready: bool = True) -> Path:
    venv = home / ".productforge/observe-venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin/python").write_text("#!/bin/sh\n")
    if ready:
        (venv / capabilities.VENV_READY).write_text(json.dumps({"version": "1"}))
    return venv


def test_without_the_venv_observe_resolves_to_none(tmp_path: Path) -> None:
    res = resolution(tmp_path)
    assert res.provider == "none" and not res.required
    assert res.installable == ["productforge:observe-recorder"]


def test_a_ready_venv_is_detected(tmp_path: Path) -> None:
    venv = fake_venv(tmp_path)
    res = resolution(tmp_path)
    assert res.provider == "productforge:observe-recorder" and res.kind == "local"
    assert res.version == "1" and res.invoke == "observe/recorder.py"
    (venv / capabilities.VENV_READY).unlink()  # half-installed: no marker
    assert resolution(tmp_path).provider == "none"


def test_never_offered_at_init(tmp_path: Path) -> None:
    reg = capabilities.load_registry()
    resolved = capabilities.resolve(
        reg, capabilities.detect(reg, set(), home=tmp_path, plugin_list=[])
    )
    assert CAP not in capabilities.offers(reg, resolved, {}, [])


def test_install_prints_and_installs_nothing_without_confirmation(tmp_path: Path) -> None:
    payload, code = deps.install(
        None, CAP, None, confirmed=False, ack_third_party=False, home=tmp_path
    )
    assert code == 0 and payload["executed"] is False
    venv = str(tmp_path / ".productforge/observe-venv")
    assert payload["commands"][0] == ["python3.11", "-m", "venv", venv]
    assert payload["commands"][-1][-3:] == ["install", "--no-shell", "chromium"]
    assert "540 MB" in payload["consent_text"] and "system Python" in payload["consent_text"]
    assert not (tmp_path / ".productforge").exists()


def test_consent_is_recorded_and_asked_again_when_the_text_changes(
    tasklet_plan: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    assert observe.record_consent(tasklet_plan, confirmed=False)["consented"] is False
    out = observe.record_consent(tasklet_plan, confirmed=True)
    assert out["consented"] is True and state.load(tasklet_plan).observe_consent["text_sha256"]
    observe.require_consent(tasklet_plan)  # no error
    monkeypatch.setattr(observe, "CONSENT_TEXT", observe.CONSENT_TEXT + " Changed.")
    status = observe.consent_status(state.load(tasklet_plan))
    assert status["consented"] is False and status["stale"] is True


def test_consent_text_names_the_hard_rules() -> None:
    for phrase in ("your own account", "never clicks for you", "terms of service",
                   "Passwords", "never stored", "discard"):  # fmt: skip
        assert phrase in observe.CONSENT_TEXT, phrase


def test_ingest_needs_a_session(pf_cli, tasklet_plan: Path) -> None:  # type: ignore[no-untyped-def]
    code, out, _ = pf_cli("observe", "ingest", "--workspace", str(tasklet_plan), "--json")
    assert code == 2 and json.loads(out)["error"] == "OBSERVE_NO_SESSION"


def test_cli_status_without_a_session(pf_cli, tasklet_discovery: Path) -> None:  # type: ignore[no-untyped-def]
    code, out, _ = pf_cli("observe", "status", "--workspace", str(tasklet_discovery), "--json")
    assert code == 2 and json.loads(out)["error"] == "OBSERVE_NO_SESSION"
