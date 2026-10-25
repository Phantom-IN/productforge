from __future__ import annotations

import json
from pathlib import Path

from conftest import TASKLET

from pflib import config, features, gates, render, state


def failing(ws: Path) -> list[str]:
    return gates.evaluate(ws, "SCOPE_DEFINED").failing()


def details(ws: Path) -> dict[str, str]:
    return {r.id: r.detail for r in gates.evaluate(ws, "SCOPE_DEFINED").results}


def test_passing_fixture_passes_every_condition() -> None:
    report = gates.evaluate(TASKLET / "SCOPE_DEFINED", "SCOPE_DEFINED")
    assert report.passed, [r.to_dict() for r in report.results if not r.passed]
    d = details(TASKLET / "SCOPE_DEFINED")
    assert d["G-SC-ALL-SCORED"] == "all 31 features have one score card"
    assert d["G-SC-OVERRIDES-REASONED"] == "3 overrides, all with reasons"
    assert d["G-SC-REQUIREMENTS-COVER-BUILD"] == "all 18 V1 features are covered by requirements"


def test_failing_fixture_lists_exact_failures() -> None:
    ws = TASKLET / "SCOPE_DEFINED_FAILING"
    assert failing(ws) == ["G-SC-UNKNOWNS-DEFAULTED", "G-SC-CONFLICTS-RESOLVED"]
    d = details(ws)
    assert "U-009, U-010, U-011" in d["G-SC-UNKNOWNS-DEFAULTED"]
    assert "D-045" in d["G-SC-CONFLICTS-RESOLVED"]


def test_a_hand_edited_view_fails_decisions_computed(tasklet_scope: Path) -> None:
    p = tasklet_scope / "research/FEATURE_MATRIX.md"
    p.write_text(p.read_text().replace("| yes | BUILD NOW | 19 |", "| yes | BUILD NOW | 25 |", 1))
    assert "G-SC-DECISIONS-COMPUTED" in failing(tasklet_scope)
    assert "research/FEATURE_MATRIX.md" in details(tasklet_scope)["G-SC-DECISIONS-COMPUTED"]


def test_gate_passing_fixture_advances_to_architecture_locked(pf_cli, tasklet_scope: Path) -> None:  # type: ignore[no-untyped-def]
    code, out, err = pf_cli(
        "advance", "--to", "ARCHITECTURE_LOCKED", "--confirmed", "--workspace", str(tasklet_scope),
        "--json",
    )  # fmt: skip
    assert code == 0, err
    st = state.load(tasklet_scope)
    assert st.state.value == "ARCHITECTURE_LOCKED" and st.locks["SCOPE_DEFINED"]
    assert json.loads(out)["gate"]["passed"] is True


# ---------------------------------------------------------------- v3 phase 03: scope safeguards


def _strip_override(ws: Path, sc: str) -> None:
    p = ws / "spec/PARITY_MATRIX.md"
    lines, out, inside = p.read_text().splitlines(keepends=True), [], False
    for line in lines:
        if line.startswith("### "):
            inside = line.startswith(f"### {sc} ")
        if inside and line.startswith(("- Override decision:", "- Override reason:")):
            continue
        out.append(line)
    p.write_text("".join(out))
    render.render_all(ws)


def test_competitor_signal_passes_with_researched_competitors(tasklet_scope: Path) -> None:
    assert details(tasklet_scope)["G-SC-COMPETITOR-SIGNAL"] == "3 competitors researched"


def test_competitor_signal_fails_then_passes_with_a_waiver(pf_cli, tasklet_scope: Path) -> None:  # type: ignore[no-untyped-def]
    ws = tasklet_scope
    config.write_config(ws, {"competitors.min_researched": 4})
    assert "G-SC-COMPETITOR-SIGNAL" in failing(ws)
    assert "3 of 4 competitors" in details(ws)["G-SC-COMPETITOR-SIGNAL"]
    code, out, err = pf_cli(
        "waive", "competitors", "--reason", "Greenfield niche", "--workspace", str(ws), "--json"
    )
    assert code == 2 and "--confirmed" in err
    assert "G-SC-COMPETITOR-SIGNAL" in failing(ws)
    code, out, err = pf_cli(
        "waive", "competitors", "--reason", "Greenfield niche", "--confirmed",
        "--workspace", str(ws), "--json",
    )  # fmt: skip
    assert code == 0, err
    assert json.loads(out) == {"waived": True, "reason": "Greenfield niche"}
    assert "G-SC-COMPETITOR-SIGNAL" not in failing(ws)
    assert details(ws)["G-SC-COMPETITOR-SIGNAL"] == "waived: Greenfield niche"
    status = json.loads(pf_cli("status", "--workspace", str(ws), "--json")[1])
    assert status["waivers"]["competitors"]["reason"] == "Greenfield niche"


def test_headline_detection_uses_evidence_and_surface_of_the_target(tasklet_scope: Path) -> None:
    headline = features.headline_features(tasklet_scope)
    assert {"F-019", "F-031"} <= headline
    assert "F-002" not in headline  # cites docs only


def test_headline_categories_are_configurable(tasklet_scope: Path) -> None:
    config.write_config(tasklet_scope, {"scope.headline_categories": []})
    assert features.headline_features(tasklet_scope) == set()


def test_headline_cut_without_override_fails_until_reviewed(pf_cli, tasklet_scope: Path) -> None:  # type: ignore[no-untyped-def]
    ws = tasklet_scope
    _strip_override(ws, "SC-019")
    assert "G-SC-HEADLINE-REVIEWED" in failing(ws)
    assert "SC-019" in details(ws)["G-SC-HEADLINE-REVIEWED"]
    code, _, err = pf_cli(
        "override", "F-019", "--decision", "BUILD SIMPLIFIED", "--reason", "Search is marketed",
        "--workspace", str(ws), "--json",
    )  # fmt: skip
    assert code == 0, err
    assert "G-SC-HEADLINE-REVIEWED" not in failing(ws)
    spec = render.regions((ws / "spec/PRODUCT_SPEC.md").read_text())
    assert "F-031" in spec["headline-cuts"] and "single free plan" in spec["headline-cuts"]
    assert "F-019" not in spec["headline-cuts"]  # no longer cut
