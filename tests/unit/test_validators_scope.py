from __future__ import annotations

from pathlib import Path

import pytest

from pflib import render, validators

PM = "spec/PARITY_MATRIX.md"


def codes(ws: Path) -> list[str]:
    return [f.code for f in validators.run(ws)]


def edit(ws: Path, old: str, new: str, rel: str = PM) -> None:
    p = ws / rel
    text = p.read_text()
    assert old in text, old
    p.write_text(text.replace(old, new, 1))


def test_fixture_is_clean(tasklet_scope: Path) -> None:
    assert validators.run(tasklet_scope) == []


@pytest.mark.parametrize(
    "old, new, code",
    [
        ("- Core value: 1 — supports the core loop\n- User frequency: 0",
         "- Core value: 7 — off the scale\n- User frequency: 0", "BAD_SCORE"),
        ("- Future: no\n", "- Future: someday\n", "BAD_ENUM"),
        ("- Override decision: BUILD SIMPLIFIED", "- Override decision: SHIP IT", "BAD_ENUM"),
        ("- Simplification: Boards refresh on focus and every 30 s; no push channel in V1\n", "",
         "SIMPLIFICATION_MISSING"),
        ("- External service: Object storage with signed download links\n", "",
         "EXTERNAL_SERVICE_MISSING"),
        ("- Feature: F-031\n", "- Feature: F-030\n", "DUPLICATE_SCORE"),
        ("- Feature: F-031\n", "- Feature: D-001\n", "WRONG_REF_TYPE"),
        ("- Override reason: Live updates are the target's selling point (D-007); V1 polls "
         "instead of pushing\n", "", "OVERRIDE_NO_REASON"),
    ],
)  # fmt: skip
def test_score_card_findings(tasklet_scope: Path, old: str, new: str, code: str) -> None:
    edit(tasklet_scope, old, new)
    assert code in codes(tasklet_scope)


def test_model_written_priorities_are_refused(tasklet_scope: Path) -> None:
    edit(tasklet_scope, "- Future: no\n", "- Future: no\n- Priority: 14\n")
    assert "FIELD_NOT_YET_ALLOWED" in codes(tasklet_scope)


def test_unscored_feature_once_scoring_started(tasklet_scope: Path) -> None:
    p = tasklet_scope / PM
    text = p.read_text()
    p.write_text(text[: text.index("\n### SC-031 ")] + "\n")
    render.render_all(tasklet_scope)
    found = [f for f in validators.run(tasklet_scope) if f.code == "FEATURE_UNSCORED"]
    assert len(found) == 1 and "F-031" in found[0].message and found[0].artifact == PM


def test_v1_features_need_requirements(tasklet_scope: Path) -> None:
    edit(tasklet_scope, "- Features: F-006\n", "- Features: F-005\n", rel="spec/PRODUCT_SPEC.md")
    found = [f for f in validators.run(tasklet_scope) if f.code == "FEATURE_WITHOUT_REQUIREMENT"]
    assert [(f.record_id, "F-006" in f.message) for f in found] == [("SC-006", True)]


def test_before_scoping_nothing_is_required(tasklet_product_model: Path) -> None:
    assert validators.run(tasklet_product_model) == []  # no PARITY_MATRIX yet → no FEATURE_UNSCORED
