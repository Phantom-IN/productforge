from __future__ import annotations

from pathlib import Path

from pflib import merge, render, validators, workspace

TREE = """\
- E-01 Workspace
  - E-03 Membership · also E-02 User (N:1)
  - E-04 Project · also E-03 Membership (N:1)
  - E-05 Task · also E-04 Project (N:1), E-03 Membership (N:1), E-07 Label (N:M)
    - E-06 Comment · also E-02 User (N:1)
    - E-08 Attachment
    - E-11 Activity event · also E-02 User (N:1)
  - E-07 Label · also E-05 Task (N:M)
  - E-10 Integration
- E-02 User
  - E-09 Notification · also E-05 Task (N:1)
"""


def regions(ws: Path, rel: str) -> dict[str, str]:
    return render.regions((ws / rel).read_text())


def test_relationship_tree_roots_at_the_tenancy_entity(tasklet_product_model: Path) -> None:
    assert regions(tasklet_product_model, "spec/DOMAIN_MODEL.md")["relationship-tree"] == TREE


def test_identity_table(tasklet_product_model: Path) -> None:
    table = regions(tasklet_product_model, "spec/DOMAIN_MODEL.md")["identity"].splitlines()
    assert table[0] == (
        "| Entity | Identity scheme | Human-readable key | Stable after creation? | Evidence |"
    )
    assert table[4] == "| E-03 Membership | (workspace, user) pair | — | yes | D-026, D-027 |"
    assert len(table) == 2 + 11


def test_permissions_matrix(tasklet_product_model: Path) -> None:
    rows = regions(tasklet_product_model, "spec/PERMISSIONS_MATRIX.md")["permissions"].splitlines()
    assert rows[0] == (
        "| Resource | Action | RL-01 Owner | RL-02 Admin | RL-03 Member | RL-04 Guest | Rule |"
    )
    assert rows[2] == "| E-01 Workspace | manage-billing | ✓ | ✓ | ✗ | ✗ | PR-001 |"
    tasks = [r.split(" | ")[1] for r in rows if r.startswith("| E-05 Task")]
    assert tasks == ["create", "read", "update", "delete"]  # CRUD order, then custom verbs
    assert render.render_all(tasklet_product_model) == []  # fixture views are fresh


def test_missing_cell_renders_a_dash_and_is_flagged(tasklet_product_model: Path) -> None:
    p = tasklet_product_model / "spec/PERMISSIONS_MATRIX.md"
    p.write_text(p.read_text().replace("RL-01 ✓, RL-02 ✓, RL-03 ✗, RL-04 ✗", "RL-01 ✓", 1))
    assert render.render_all(tasklet_product_model) == ["spec/PERMISSIONS_MATRIX.md"]
    rows = regions(tasklet_product_model, "spec/PERMISSIONS_MATRIX.md")["permissions"]
    assert "| E-01 Workspace | manage-billing | ✓ | — | — | — | PR-001 |" in rows
    assert [f.code for f in validators.run(tasklet_product_model)] == ["PERMISSION_CELL_MISSING"]


def test_first_merge_seeds_the_file_from_its_template(tasklet_product_model: Path) -> None:
    ws = tasklet_product_model
    for rel in ("spec/DOMAIN_MODEL.md", "spec/PERMISSIONS_MATRIX.md"):
        (ws / rel).unlink()
    run_id, path = workspace.create_staging_run(ws, "domain-architect")
    (path / "spec").mkdir()
    (path / "spec/PERMISSIONS_MATRIX.md").write_text(
        "## Roles\n\n### RL-?1 — Owner\n- Description: Owns the workspace\n- Scope: workspace\n"
        "- Inherits: none\n- Evidence: D-027\n- Confidence: CONFIRMED\n"
    )
    report = merge.merge(ws, run_id)
    text = (ws / "spec/PERMISSIONS_MATRIX.md").read_text()
    assert text.startswith("# Permissions matrix — Tasklet\n")
    assert "\n## Roles\n\n### RL-01 — Owner\n" in text and text.index("## Roles") < text.index(
        "## Rules"
    )
    assert report.rendered == []  # no rules yet: the template's placeholder stays as is
    assert "_No permission rules yet._" in text
    assert validators.run(ws, artifact="spec/PERMISSIONS_MATRIX.md") == []
