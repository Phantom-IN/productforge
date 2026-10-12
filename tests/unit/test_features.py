from __future__ import annotations

from pathlib import Path

from pflib import features, merge, records, workspace


def stage(ws: Path, text: str) -> str:
    run_id, path = workspace.create_staging_run(ws, "product-analyst")
    (path / "research").mkdir()
    (path / "research/FEATURE_MATRIX.md").write_text(text)
    return run_id


def test_feature_plan(tasklet_product_model: Path) -> None:
    plan = features.plan(tasklet_product_model)
    assert [d["name"] for d in plan["domains"]] == [
        "Tasks & boards", "Projects", "Collaboration", "Workspace & access", "Integrations & API",
    ]  # fmt: skip
    assert plan["features"] == 31 and plan["features_per_domain"]["Projects"] == 3
    assert plan["empty_domains"] == [] and plan["surfaces_without_features"] == []
    assert plan["max_parallel"] == 4 and plan["over_soft_cap"] is False
    assert plan["per_domain_budget"] == 24  # 120 soft cap over 5 domains


def test_features_dedupe_by_domain_and_normalised_name(tasklet_product_model: Path) -> None:
    text = (
        "### F-?1 — Labels!\n- Domain: Tasks & boards\n- Feature: labels\n- Parent: F-001\n"
        "- Surface: PS-03\n- Evidence: D-013\n- Confidence: CONFIRMED\n- Plan tier: all\n"
        "- Complexity: Low\n- Notes:\n\n"
        "### F-?2 — Labels\n- Domain: Projects\n- Feature: Labels\n- Parent: F-011\n"
        "- Surface: PS-04\n- Evidence: D-014\n- Confidence: CONFIRMED\n- Plan tier: all\n"
        "- Complexity: Low\n- Notes:\n"
    )
    report = merge.merge(tasklet_product_model, stage(tasklet_product_model, text))
    assert report.id_map["F-?1"] == "F-005"  # same domain + same normalised name → existing
    assert report.id_map["F-?2"] == "F-032"  # same name, different domain → a new feature
    doc = records.parse_document((tasklet_product_model / "research/FEATURE_MATRIX.md").read_text())
    rec = doc.record("F-005")
    assert rec is not None and rec.get("Evidence") == "D-014, D-013"


def test_domains_section_is_merged_from_staging(tasklet_product_model: Path) -> None:
    run_id, path = workspace.create_staging_run(tasklet_product_model, "product-analyst")
    (path / "research").mkdir()
    (path / "research/FEATURE_MATRIX.md").write_text(
        "## Domains\n\n- Tasks & boards: tasks (D-001)\n"
        "- Reporting: dashboards and exports (D-036)\n"
    )
    report = merge.merge(tasklet_product_model, run_id)
    assert report.sections_updated == ["research/FEATURE_MATRIX.md"]
    assert report.ignored_prose_lines == 0
    assert [d["name"] for d in features.domains(tasklet_product_model)] == [
        "Tasks & boards",
        "Reporting",
    ]
    plan = features.plan(tasklet_product_model)
    assert plan["empty_domains"] == ["Reporting"]
    assert plan["features_in_unlisted_domains"]["Projects"] == 3


def test_superseding_a_feature_removes_it_from_views_and_counts(
    tasklet_product_model: Path,
) -> None:
    from pflib import render, validators

    text = (
        "### F-?1 — Due dates\n- Domain: Tasks & boards\n- Feature: Due dates\n- Parent: F-001\n"
        "- Surface: PS-03\n- Evidence: D-023\n- Confidence: CONFIRMED\n- Plan tier: all\n"
        "- Complexity: Low\n- Notes:\n\n### AMEND F-003\n- Status: superseded-by F-?1\n"
        "- Why: renamed; reminders are not a separate capability.\n"
    )
    report = merge.merge(tasklet_product_model, stage(tasklet_product_model, text))
    assert report.amended == ["F-003"] and report.new_ids == ["F-032"]
    tree = render.regions((tasklet_product_model / "research/FEATURE_MATRIX.md").read_text())
    assert "F-003" not in tree["hierarchy"] and "F-032 Due dates" in tree["hierarchy"]
    assert features.plan(tasklet_product_model)["features"] == 31
    assert validators.run(tasklet_product_model) == []
