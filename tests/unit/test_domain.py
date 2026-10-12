from __future__ import annotations

from pathlib import Path

from pflib import domain
from pflib.index import WorkspaceIndex


def test_relationship_grammar() -> None:
    rels, bad = domain.parse_relationships(
        "E-01 (N:1, required) workspace; E-?2 (N:M, optional); E-03 belongs to; "
        "E-04 (2:N, optional)"
    )
    assert [(r.target, r.cardinality, r.required, r.note) for r in rels] == [
        ("E-01", "N:1", True, "workspace"),
        ("E-?2", "N:M", False, ""),
    ]
    assert bad == ["E-03 belongs to", "E-04 (2:N, optional)"]
    assert domain.parse_relationships("none") == ([], [])
    assert domain.parse_relationships("") == ([], [])


def test_grant_grammar() -> None:
    cells, bad = domain.parse_grants("RL-01 ✓, RL-02 → ✗, RL-03: Limited, RL-?4 ?, RL-05 yes")
    assert cells == {"RL-01": "✓", "RL-02": "✗", "RL-03": "Limited", "RL-?4": "?"}
    assert bad == ["RL-05 yes"]


def test_deletion_kind() -> None:
    assert domain.deletion_kind("archive — can be restored") == "archive"
    assert domain.deletion_kind("Soft-delete for 30 days") == "soft-delete"
    assert domain.deletion_kind("archived forever") is None
    assert domain.deletion_kind("gone") is None


def test_mutability(tasklet_product_model: Path) -> None:
    index = WorkspaceIndex(tasklet_product_model)
    ents = {e.id: e for e in domain.active(index, "E")}
    feats = {f.id: f for _, f in index.records("F")}
    assert domain.is_mutable(ents["E-05"], feats)  # lists mutable fields
    assert not domain.is_mutable(ents["E-11"], feats)  # "none — append-only"
    assert domain.is_mutable(ents["E-08"], feats)  # immutable fields, but "Attachments" feature
    assert not domain.is_mutable(ents["E-09"], feats)


def test_permission_cells(tasklet_product_model: Path) -> None:
    cells = domain.permission_cells(WorkspaceIndex(tasklet_product_model))
    assert cells["rules"] == 13 and cells["roles"] == 4 and cells["missing"] == 0
    assert cells["cells"] == {"✓": 31, "✗": 13, "Limited": 3, "?": 5}
    assert sum(cells["cells"].values()) == 13 * 4


def test_parent_cycle_entities_are_still_shown(tmp_path: Path) -> None:
    from pflib import catalog

    body = "".join(
        f"\n### E-0{i} — {name}\n- Relationships: E-0{other} (N:1, required)\n"
        for i, name, other in ((1, "A", 2), (2, "B", 1))
    )
    (tmp_path / "spec").mkdir()
    (tmp_path / catalog.DOMAIN_MODEL_PATH).write_text("# Domain model\n\n## Records\n" + body)
    lines = domain.relationship_tree(WorkspaceIndex(tmp_path))
    assert {ln.split(" ·")[0].strip() for ln in lines} == {"- E-01 A", "- E-02 B"}
