from __future__ import annotations

import json
from pathlib import Path

from conftest import TASKLET

from pflib import gates, state


def failing(ws: Path) -> list[str]:
    return gates.evaluate(ws, "PRODUCT_MODEL").failing()


def details(ws: Path) -> dict[str, str]:
    return {r.id: r.detail for r in gates.evaluate(ws, "PRODUCT_MODEL").results}


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new, 1))


def test_passing_fixture_passes_every_condition() -> None:
    report = gates.evaluate(TASKLET / "PRODUCT_MODEL", "PRODUCT_MODEL")
    assert report.passed, [r.to_dict() for r in report.results if not r.passed]
    d = details(TASKLET / "PRODUCT_MODEL")
    assert d["G-PM-PERMISSIONS-COVERAGE"] == "13 rules × 4 roles, 5 unknown cells"
    assert d["G-PM-WORKFLOW-PER-DOMAIN"].startswith("all 5 core domains")


def test_failing_fixture_lists_exact_failures() -> None:
    ws = TASKLET / "PRODUCT_MODEL_FAILING"
    assert failing(ws) == [
        "G-PM-WORKFLOW-PER-DOMAIN", "G-PM-INTEGRATIONS-COMPLETE", "G-PM-INFERENCE-COMPLETE",
    ]  # fmt: skip
    d = details(ws)
    assert "Integrations & API" in d["G-PM-WORKFLOW-PER-DOMAIN"]
    assert (
        "W-008" in d["G-PM-INFERENCE-COMPLETE"]
        and "(/productforge model" in d["G-PM-INTEGRATIONS-COMPLETE"]
    )


def test_surface_without_features_fails(tasklet_product_model: Path) -> None:
    fm = tasklet_product_model / "research/FEATURE_MATRIX.md"
    edit(fm, "- Surface: PS-07", "- Surface: PS-03")  # F-025 → only feature on PS-07?
    text = fm.read_text()
    fm.write_text(text.replace("- Surface: PS-07", "- Surface: PS-03"))
    assert "G-PM-SURFACE-FEATURES" in failing(tasklet_product_model)
    assert "PS-07" in details(tasklet_product_model)["G-PM-SURFACE-FEATURES"]


def test_uncovered_workflow_fails_inference(tasklet_product_model: Path) -> None:
    ai = tasklet_product_model / "research/architecture-inference.md"
    edit(ai, "- Derived from: W-008, E-04", "- Derived from: E-04")
    assert failing(tasklet_product_model) == ["G-VALIDATE-CLEAN", "G-PM-INFERENCE-COMPLETE"]
    # (the stale workflow-coverage view is the validation error)
    assert "W-008" in details(tasklet_product_model)["G-PM-INFERENCE-COMPLETE"]


def test_permission_gap_fails_coverage(tasklet_product_model: Path) -> None:
    pm = tasklet_product_model / "spec/PERMISSIONS_MATRIX.md"
    edit(pm, "RL-01 ✓, RL-02 ✓, RL-03 ✗, RL-04 ✗", "RL-01 ✓, RL-02 ✓, RL-03 ✗")
    assert "G-PM-PERMISSIONS-COVERAGE" in failing(tasklet_product_model)
    assert (
        "PR-001 PERMISSION_CELL_MISSING"
        in details(tasklet_product_model)["G-PM-PERMISSIONS-COVERAGE"]
    )


def test_gate_passing_fixture_advances_to_scope_defined(
    pf_cli, tasklet_product_model: Path
) -> None:  # type: ignore[no-untyped-def]
    ws = str(tasklet_product_model)
    code, out, _ = pf_cli("advance", "--to", "SCOPE_DEFINED", "--workspace", ws, "--json")
    assert code == 0 and state.load(tasklet_product_model).state.value == "PRODUCT_MODEL"
    assert json.loads(out)["gate"]["passed"] is True  # report only, nothing changed
    code, out, err = pf_cli(
        "advance", "--to", "SCOPE_DEFINED", "--confirmed", "--workspace", ws, "--json"
    )
    assert code == 0, err
    st = state.load(tasklet_product_model)
    assert st.state.value == "SCOPE_DEFINED" and st.locks["PRODUCT_MODEL"]


def test_failing_fixture_cannot_advance(pf_cli, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    import shutil

    ws = tmp_path / "pmf"
    shutil.copytree(TASKLET / "PRODUCT_MODEL_FAILING", ws)
    code, _, _ = pf_cli(
        "advance", "--to", "SCOPE_DEFINED", "--confirmed", "--workspace", str(ws), "--json"
    )
    assert code == 1 and state.load(ws).state.value == "PRODUCT_MODEL"
