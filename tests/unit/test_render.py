from __future__ import annotations

from pathlib import Path

from pflib import merge, render, state, validators, workspace


def test_render_is_idempotent_and_leaves_outside_text_alone(tasklet_product_model: Path) -> None:
    fm = tasklet_product_model / "research/FEATURE_MATRIX.md"
    before = fm.read_text()
    assert render.render_all(tasklet_product_model) == []  # fixture is already fresh
    fm.write_text(before.replace("## Domains\n", "## Domains\n\nA hand-written note.\n"))
    assert render.render_all(tasklet_product_model) == []
    assert "A hand-written note." in fm.read_text()


def test_stale_or_edited_region_is_flagged_and_rerendered(tasklet_product_model: Path) -> None:
    fm = tasklet_product_model / "research/FEATURE_MATRIX.md"
    fm.write_text(fm.read_text().replace("| F-001 | Tasks & boards | Tasks |", "| F-001 | X | Y |"))
    assert [f.code for f in validators.run(tasklet_product_model)] == ["GENERATED_REGION_EDITED"]
    assert render.render_all(tasklet_product_model) == ["research/FEATURE_MATRIX.md"]
    assert validators.run(tasklet_product_model) == []


def test_missing_region_is_created_under_its_heading(tmp_path: Path) -> None:
    text = "# Product surfaces\n\n## Records\n\n### PS-01 — A\n- Purpose: x\n"
    out = render.apply(
        text, {"surface-features": "| a |\n"}, {"surface-features": "## Surface → features"}
    )
    assert out == text + (
        "\n## Surface → features\n\n<!-- pf:generated:start surface-features -->\n| a |\n"
        "<!-- pf:generated:end -->\n"
    )
    assert render.apply(out, {"surface-features": "| a |\n"}, {"surface-features": "## X"}) == out


def test_hierarchy_and_matrix_shape(tasklet_product_model: Path) -> None:
    regions = render.regions((tasklet_product_model / "research/FEATURE_MATRIX.md").read_text())
    tree = regions["hierarchy"].splitlines()
    assert tree[0] == "- **Collaboration**"
    assert "  - F-001 Tasks" in tree and "    - F-002 Assignment" in tree
    header = regions["matrix"].splitlines()[0]
    assert header == "| " + " | ".join(render.MATRIX_COLUMNS) + " |"
    assert regions["matrix"].count("\n| F-") == 31


def test_lock_hashes_ignore_generated_regions(tasklet_product_model: Path) -> None:
    ps = tasklet_product_model / "research/product-surfaces.md"
    locked = state.load(tasklet_product_model).locks["DISCOVERY"]
    assert "PS-03" in locked
    ps.write_text(
        ps.read_text().replace("<!-- pf:generated:end -->", "extra\n<!-- pf:generated:end -->")
    )
    codes = [f.code for f in validators.run(tasklet_product_model)]
    assert codes == ["GENERATED_REGION_EDITED"]  # a stale view, not a LOCK_VIOLATION


def test_merge_renders_and_links_surfaces(tasklet_product_model: Path) -> None:
    run_id, path = workspace.create_staging_run(tasklet_product_model, "product-analyst")
    (path / "research").mkdir()
    (path / "research/FEATURE_MATRIX.md").write_text(
        "### F-?1 — Keyboard shortcuts\n- Domain: Tasks & boards\n- Feature: Keyboard shortcuts\n"
        "- Parent: F-008\n- Surface: PS-03\n- Evidence: D-006\n- Confidence: PROBABLE\n"
        "- Plan tier: all\n- Complexity: Low\n- Notes:\n"
    )
    report = merge.merge(tasklet_product_model, run_id)
    assert report.new_ids == ["F-032"]
    assert set(report.rendered) == {"research/FEATURE_MATRIX.md", "research/product-surfaces.md"}
    regions = render.regions((tasklet_product_model / "research/FEATURE_MATRIX.md").read_text())
    assert "    - F-032 Keyboard shortcuts" in regions["hierarchy"]
    surfaces = render.regions((tasklet_product_model / "research/product-surfaces.md").read_text())
    assert "F-031" in surfaces["surface-features"] and "F-032" in surfaces["surface-features"]
    assert validators.run(tasklet_product_model) == []


def test_surface_view_waits_for_features(tasklet_discovery: Path) -> None:
    assert render.render_all(tasklet_discovery) == []  # no features yet → no surface table
