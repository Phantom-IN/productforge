from __future__ import annotations

import json
from pathlib import Path

import pytest

from pflib import render, score, validators, workspace
from pflib.errors import UsageError


def row(ws: Path, feature: str) -> score.Row:
    return next(r for r in score.evaluate(ws) if r.feature == feature)


def test_user_override_is_an_amendment_through_merge(pf_cli, tasklet_scope: Path) -> None:  # type: ignore[no-untyped-def]
    ws = tasklet_scope
    assert row(ws, "F-005").decision == score.DEFER
    code, out, err = pf_cli(
        "override",
        "F-005",
        "--decision",
        "BUILD NOW",
        "--reason",
        "Our pilot teams live in labels",
        "--workspace",
        str(ws),
        "--json",
    )
    assert code == 0, err
    payload = json.loads(out)
    assert payload["computed"] == score.DEFER and payload["decision"] == score.BUILD_NOW
    assert row(ws, "F-005").override == score.BUILD_NOW
    event = [e for e in workspace.read_history(ws) if e["event"] == "amend"][-1]
    assert event["id"] == "SC-005" and "pilot teams" in event["why"]
    parity = render.regions((ws / "spec/PARITY_MATRIX.md").read_text())
    assert (
        "SC-005 F-005: computed DEFER → BUILD NOW — Our pilot teams live in labels"
        in parity["overrides"]
    )
    # labels are now in V1 without a requirement — the validator says so
    assert "FEATURE_WITHOUT_REQUIREMENT" in [f.code for f in validators.run(ws)]


def test_clearing_an_override(tasklet_scope: Path) -> None:
    out = score.record_override(tasklet_scope, "F-009", None, "the user prefers the computed call")
    assert out["override"] is None and out["decision"] == score.DEFER


@pytest.mark.parametrize(
    "feature, decision, reason, code",
    [("F-005", "SHIP IT", "x", "BAD_DECISION"), ("F-005", score.DROP, " ", "OVERRIDE_NO_REASON"),
     ("F-999", score.DROP, "x", "NO_SCORE_CARD")],
)  # fmt: skip
def test_bad_overrides_are_refused(
    tasklet_scope: Path, feature: str, decision: str, reason: str, code: str
) -> None:
    with pytest.raises(UsageError) as info:
        score.record_override(tasklet_scope, feature, decision, reason)
    assert info.value.code == code
