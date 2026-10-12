from __future__ import annotations

from pathlib import Path

import pytest

from pflib import validators

PM = "spec/PERMISSIONS_MATRIX.md"


def codes(ws: Path) -> list[str]:
    return [f.code for f in validators.run(ws)]


def edit(ws: Path, rel: str, old: str, new: str) -> None:
    p = ws / rel
    text = p.read_text()
    assert old in text, old
    p.write_text(text.replace(old, new, 1))


@pytest.mark.parametrize(
    "old, new, code",
    [
        (
            "RL-01 ✓, RL-02 ✓, RL-03 ✗, RL-04 ✗",
            "RL-01 ✓, RL-02 ✓, RL-03 ✗",
            "PERMISSION_CELL_MISSING",
        ),
        ("RL-01 ✓, RL-02 ✓, RL-03 ✗, RL-04 ✗", "RL-01 ✓, RL-02 ✓, RL-03 ✗, RL-04 no", "BAD_GRANT"),
        (
            "RL-01 ✓, RL-02 ✓, RL-03 ✗, RL-04 ✗",
            "RL-01 ✓, RL-02 ✓, RL-03 ✗, RL-04 ?",
            "UNKNOWN_CELL_NO_U",
        ),
        (
            "RL-01 ✓, RL-02 ✓, RL-03 ✗, RL-04 ✗",
            "RL-01 ✓, RL-02 ✓, RL-03 Limited, RL-04 ✗",
            "LIMITED_WITHOUT_MEANS",
        ),
        ("- Resource: E-01", "- Resource: RL-01", "WRONG_REF_TYPE"),
        (
            "RL-01 ✓, RL-02 ✓, RL-03 ✗, RL-04 ✗",
            "RL-01 ✓, RL-02 ✓, RL-03 ✗, RL-04 ✗, RL-09 ✗",
            "DANGLING_REF",
        ),
        ("- Scope: workspace", "- Scope: everywhere", "BAD_ENUM"),
    ],
)  # PR-001 (Manage workspace billing) is the first rule in the fixture
def test_rule_findings(tasklet_product_model: Path, old: str, new: str, code: str) -> None:
    edit(tasklet_product_model, PM, old, new)
    assert code in codes(tasklet_product_model)


def test_a_new_role_needs_a_cell_in_every_rule(tasklet_product_model: Path) -> None:
    edit(tasklet_product_model, PM, "\n## Rules\n", "\n### RL-05 — Viewer\n- Description: Reads "
         "everything\n- Scope: workspace\n- Inherits: none\n- Evidence: D-027\n"
         "- Confidence: CONFIRMED\n\n## Rules\n")  # fmt: skip
    missing = [f for f in validators.run(tasklet_product_model)
               if f.code == "PERMISSION_CELL_MISSING"]  # fmt: skip
    assert len(missing) == 13 and all("RL-05" in f.message for f in missing)


def test_mutable_entity_without_rules(tasklet_product_model: Path) -> None:
    # E-09 Notification: "Mutable fields: none" and no mutating feature → no rule needed
    assert "ENTITY_WITHOUT_PERMISSIONS" not in codes(tasklet_product_model)
    edit(tasklet_product_model, "spec/DOMAIN_MODEL.md", "- Mutable fields: none\n",
         "- Mutable fields: read state\n")  # fmt: skip
    found = [f for f in validators.run(tasklet_product_model)]
    assert [(f.code, f.record_id) for f in found] == [("ENTITY_WITHOUT_PERMISSIONS", "E-09")]


def test_rejected_rules_do_not_count(tasklet_product_model: Path) -> None:
    edit(tasklet_product_model, PM, "- Evidence: D-039, D-004\n- Confidence: CONFIRMED\n",
         "- Evidence: D-039, D-004\n- Confidence: CONFIRMED\n- Status: rejected\n"
         "- Reason: duplicate\n")  # fmt: skip
    found = validators.run(tasklet_product_model)
    assert ("ENTITY_WITHOUT_PERMISSIONS", "E-08") in [(f.code, f.record_id) for f in found]


def test_a_record_cannot_supersede_itself(tasklet_product_model: Path) -> None:
    old = "- Evidence: D-039, D-004\n- Confidence: CONFIRMED\n"
    edit(tasklet_product_model, PM, old, old + "- Status: superseded-by PR-012\n")
    found = [
        f for f in validators.run(tasklet_product_model) if f.code == "SUPERSEDED_TARGET_MISSING"
    ]
    assert len(found) == 1 and "superseded by itself" in found[0].message
