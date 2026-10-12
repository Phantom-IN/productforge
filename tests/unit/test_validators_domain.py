from __future__ import annotations

from pathlib import Path

import pytest

from pflib import records, validators

DM = "spec/DOMAIN_MODEL.md"


def codes(ws: Path) -> list[str]:
    return [f.code for f in validators.run(ws)]


def edit(ws: Path, rel: str, old: str, new: str) -> None:
    p = ws / rel
    text = p.read_text()
    assert old in text, old
    p.write_text(text.replace(old, new, 1))


def test_fixture_model_is_clean_and_complete(tasklet_product_model: Path) -> None:
    assert validators.run(tasklet_product_model) == []
    doc = records.parse_document((tasklet_product_model / DM).read_text())
    assert len(doc.records) == 11
    for rec in doc.records:
        for key in ("Identity", "Lifecycle", "Deletion semantics"):
            assert rec.get(key).strip(), (rec.id, key)


@pytest.mark.parametrize(
    "old, new, code",
    [
        ("E-04 (N:1, optional) project", "E-04 (many, optional) project", "BAD_RELATIONSHIP"),
        ("E-04 (N:1, optional) project", "E-99 (N:1, optional) project", "DANGLING_REF"),
        ("E-04 (N:1, optional) project", "F-011 (N:1, optional) project", "WRONG_REF_TYPE"),
        ("- Deletion semantics: archive", "- Deletion semantics: hidden", "BAD_DELETION_SEMANTICS"),
        ("- Identity: Opaque task ID exposed by the REST API\n", "- Identity:\n", "EMPTY_FIELD"),
        ("- Stable after creation: yes", "- Stable after creation: maybe", "BAD_ENUM"),
    ],
)
def test_entity_findings(tasklet_product_model: Path, old: str, new: str, code: str) -> None:
    edit(tasklet_product_model, DM, old, new)
    assert code in codes(tasklet_product_model)


def test_inverse_cardinalities_warn_once(tasklet_product_model: Path) -> None:
    edit(tasklet_product_model, DM, "E-05 (N:M, optional) tasks", "E-05 (1:1, optional) tasks")
    found = [f for f in validators.run(tasklet_product_model)
             if f.code == "RELATIONSHIP_INCONSISTENT"]  # fmt: skip
    assert len(found) == 1 and found[0].severity == "warn" and found[0].record_id == "E-05"
    assert "expected N:M" in found[0].message


def test_one_sided_relationships_are_fine(tasklet_product_model: Path) -> None:
    # Project → Membership (owner) is declared on one side only (fixture): no finding
    assert "RELATIONSHIP_INCONSISTENT" not in codes(tasklet_product_model)


def test_superseded_entities_are_ignored(tasklet_product_model: Path) -> None:
    edit(tasklet_product_model, DM, "E-05 (N:M, optional) tasks", "E-05 (1:1, optional) tasks")
    edit(tasklet_product_model, DM, "- Related unknown: U-011\n", "- Related unknown: U-011\n"
         "- Status: superseded-by E-05\n")  # fmt: skip
    assert "RELATIONSHIP_INCONSISTENT" not in codes(tasklet_product_model)
