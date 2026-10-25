from __future__ import annotations

import json
from pathlib import Path

import pytest

from pflib import state, waivers, workspace
from pflib.errors import UsageError


def test_waive_records_reason_and_logs(tasklet_discovery: Path) -> None:
    out = waivers.waive(tasklet_discovery, "competitors", "  niche market  ")
    assert out == {"waived": True, "reason": "niche market"}
    w = state.load(tasklet_discovery).waivers["competitors"]
    assert w["reason"] == "niche market" and w["at"].endswith("Z")
    assert workspace.read_history(tasklet_discovery)[-1]["event"] == "waive"


def test_revoke_removes_the_waiver(tasklet_discovery: Path) -> None:
    waivers.waive(tasklet_discovery, "competitors", "x")
    out = waivers.waive(tasklet_discovery, "competitors", "", revoke=True)
    assert out["waived"] is False and out["revoked"] is True
    assert state.load(tasklet_discovery).waivers == {}
    assert workspace.read_history(tasklet_discovery)[-1]["event"] == "waive-revoke"


def test_a_waiver_needs_a_reason(tasklet_discovery: Path) -> None:
    with pytest.raises(UsageError) as exc:
        waivers.waive(tasklet_discovery, "competitors", "   ")
    assert exc.value.code == "WAIVER_NEEDS_REASON"


def test_unknown_waiver_is_refused(tasklet_discovery: Path) -> None:
    with pytest.raises(UsageError) as exc:
        waivers.waive(tasklet_discovery, "sources", "x")
    assert exc.value.code == "UNKNOWN_WAIVER"


def test_waiver_refused_once_scope_is_closed(tasklet_arch: Path) -> None:
    with pytest.raises(UsageError) as exc:
        waivers.waive(tasklet_arch, "competitors", "too late")
    assert exc.value.code == "WAIVER_STAGE_CLOSED"


def test_waiver_allowed_in_each_open_stage(
    tasklet_discovery: Path, tasklet_product_model: Path, tasklet_scope: Path
) -> None:
    for ws in (tasklet_discovery, tasklet_product_model, tasklet_scope):
        assert waivers.waive(ws, "competitors", "ok")["waived"] is True


def test_state_validate_dict_checks_waivers(tasklet_scope: Path) -> None:
    data = json.loads((tasklet_scope / ".productforge/state.json").read_text())
    assert state.validate_dict(data) == []
    data["waivers"] = {"competitors": {"reason": "", "at": "now"}}
    assert any("waivers.competitors" in p for p in state.validate_dict(data))
    data["waivers"] = []
    assert "waivers must be an object" in state.validate_dict(data)


def test_state_roundtrip_keeps_waivers(tasklet_scope: Path) -> None:
    waivers.waive(tasklet_scope, "competitors", "why")
    got = waivers.get(tasklet_scope, "competitors")
    assert got is not None and got["reason"] == "why"
