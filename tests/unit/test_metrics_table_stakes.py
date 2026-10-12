from __future__ import annotations

import hashlib
from pathlib import Path

from pflib import merge, metrics, records, render, validators, workspace
from pflib.index import WorkspaceIndex


def test_table_stakes_count_competitors_offering_a_feature(tasklet_product_model: Path) -> None:
    # F-001/F-014 offered by all three (C records + FS-001), F-008 by two; F-019 and F-030 by one
    assert metrics.table_stakes(tasklet_product_model) == {"F-001": 3, "F-008": 2, "F-014": 3}
    from pflib import competitors

    assert competitors.rare(WorkspaceIndex(tasklet_product_model)) == ["F-019", "F-030"]


def test_no_competitors_means_neutral(tasklet_product_model: Path) -> None:
    (tasklet_product_model / "research/COMPETITORS.md").unlink()
    assert metrics.table_stakes(tasklet_product_model) == {}


def feature_hashes(ws: Path) -> dict[str, str]:
    doc = records.parse_document((ws / "research/FEATURE_MATRIX.md").read_text())
    return {r.id: hashlib.sha256(records.serialize_record(r).encode()).hexdigest()
            for r in doc.records}  # fmt: skip


def test_a_competitor_pass_never_modifies_features(tasklet_product_model: Path) -> None:
    ws = tasklet_product_model
    before = feature_hashes(ws)
    run_id, path = workspace.create_staging_run(ws, "product-analyst")
    (path / "research").mkdir()
    (path / "research/sources.md").write_text(
        "### S-?1 — Planwise homepage\n- URL: https://planwise.example/\n"
        "- Canonical URL: https://planwise.example/\n- Category: homepage\n- Tier: 2\n"
        "- Authority: Medium\n- Relevant area: competitor:C-?1\n- Published: unknown\n"
        "- Last inspected: 2026-10-13\n- Notes:\n"
    )
    (path / "research/COMPETITORS.md").write_text(
        "## Records\n\n### C-?1 — Planwise\n- Name: Planwise\n- URL: https://planwise.example/\n"
        "- Positioning: Boards for planning\n- Target users: Small teams\n"
        "- Pricing model: Per seat\n- Table-stakes features: F-008, F-030\n"
        "- Differentiators: none\n"
        "- Common complaints: none found\n- Evidence: S-?1\n- Confidence: CONFIRMED\n"
    )
    report = merge.merge(ws, run_id)
    assert report.rendered == ["research/COMPETITORS.md"]
    assert feature_hashes(ws) == before
    assert validators.run(ws) == []
    stakes = metrics.table_stakes(ws)
    assert stakes["F-008"] == 3 and stakes["F-030"] == 2  # F-030 was rare, now table stakes
    assert (
        "| F-030 | Git commit linking | 2 | yes | 0 |"
        in render.regions((ws / "research/COMPETITORS.md").read_text())["signals"]
    )


def test_a_rerun_adds_offered_features(tasklet_product_model: Path) -> None:
    ws = tasklet_product_model
    run_id, path = workspace.create_staging_run(ws, "product-analyst")
    (path / "research").mkdir()
    (path / "research/COMPETITORS.md").write_text(
        "## Records\n\n### C-?1 — Listwise\n- Name: Listwise\n- URL: https://listwise.example/\n"
        "- Positioning: Lists first, with developer integrations\n"
        "- Target users: Engineering teams\n- Pricing model: Free for small teams; paid add-ons\n"
        "- Table-stakes features: F-008, F-025\n"
        "- Differentiators: Links commits and pull requests to tasks\n"
        "- Common complaints: Sync between devices is unreliable (S-028)\n- Evidence: S-027\n"
        "- Confidence: CONFIRMED\n"
    )
    report = merge.merge(ws, run_id)
    assert report.id_map["C-?1"] == "C-03" and report.conflicts == []
    doc = records.parse_document((ws / "research/COMPETITORS.md").read_text())
    c03 = doc.record("C-03")
    assert c03 is not None
    assert records.parse_refs(c03.get("Table-stakes features")) == [
        "F-001",
        "F-014",
        "F-008",
        "F-025",
    ]
    assert metrics.table_stakes(ws)["F-008"] == 3


def test_one_competitor_shows_no_rarity(tasklet_product_model: Path) -> None:
    from pflib import competitors

    ws = tasklet_product_model
    p = ws / "research/COMPETITORS.md"
    text = p.read_text()
    for name in ("Doable", "Listwise"):  # retire two of the three competitors
        marker = f"- Name: {name}\n"
        text = text.replace(marker, marker + "- Status: rejected\n- Reason: out of scope\n", 1)
    p.write_text(text)
    render.render_all(ws)
    index = WorkspaceIndex(ws)
    assert competitors.researched(index) == 1 and competitors.rare(index) == []
    assert metrics.table_stakes(ws) == {}
    assert "— (1 competitor)" in render.regions(p.read_text())["signals"]
