from __future__ import annotations

from pathlib import Path

from pflib import merge, records, render, validators, workflows, workspace

BODY = (
    "### W-?1 — {name}\n- Actor: Member\n- Trigger: Member exports a board\n- Features: F-008\n"
    "- Surfaces: PS-03\n- Evidence: {evidence}\n- Confidence: PROBABLE\n- Preconditions:\n"
    "- Outcome: A CSV file is downloaded\n\n## Steps\n\n"
    "1. [observed] Member opens the board menu and exports — {evidence}\n"
    "2. [implied-system] Build the export in a background job — F-008\n\n"
    "## Variations & edge cases\n\n- None found.\n\n## Engineering requirements surfaced\n\n"
    "- Step 2: an async job runner\n\n## Open questions\n\n- U-?1\n"
)
UNKNOWN = (
    "### U-?1 — Which export formats exist?\n- Question: Which formats can a board be exported "
    "to?\n- Reason it matters: Shapes the export job.\n- Available evidence: D-037\n"
    "- V1 default:\n- Impact: Low\n- Related:\n"
)


def stage(ws: Path, files: dict[str, str]) -> str:
    run_id, path = workspace.create_staging_run(ws, "ux-analyst")
    for rel, text in files.items():
        (path / rel).parent.mkdir(parents=True, exist_ok=True)
        (path / rel).write_text(text)
    return run_id


def test_new_workflow_is_named_rewritten_and_indexed(tasklet_product_model: Path) -> None:
    ws = tasklet_product_model
    unknowns = (ws / "research/UNKNOWNS.md").read_text()
    run = stage(
        ws,
        {
            "research/workflows/anything.md": BODY.format(name="Export a board!", evidence="D-037"),
            "research/UNKNOWNS.md": unknowns.split("## Records", 1)[0] + "## Records\n\n" + UNKNOWN,
        },
    )
    report = merge.merge(ws, run)
    assert report.id_map["W-?1"] == "W-009"
    path = ws / "research/workflows/W-009-export-a-board.md"
    assert "research/workflows/W-009-export-a-board.md" in report.files_written
    text = path.read_text()
    uid = report.id_map["U-?1"]
    assert text.startswith("### W-009 — Export a board!\n") and f"- {uid}\n" in text
    assert "W-?" not in text and "U-?" not in text
    assert report.rendered == ["research/README.md"]
    index = render.regions((ws / "research/README.md").read_text())["workflows"]
    assert "| W-009 | Export a board! | Member | F-008 | PROBABLE | 1 |" in index
    assert validators.run(ws) == []


def test_same_name_dedupes_into_the_existing_workflow(tasklet_product_model: Path) -> None:
    ws = tasklet_product_model
    before = sorted(p.name for p in workflows.workflow_files(ws))
    report = merge.merge(
        ws,
        stage(
            ws,
            {
                "research/workflows/x.md": BODY.format(
                    name="create a TASK", evidence="S-001"
                ).replace("- U-?1\n", "- None yet.\n")
            },
        ),
    )
    assert report.id_map["W-?1"] == "W-001" and report.deduped == 1 and report.new_ids == []
    assert sorted(p.name for p in workflows.workflow_files(ws)) == before
    doc = records.parse_document((ws / "research/workflows/W-001-create-a-task.md").read_text())
    rec = doc.record("W-001")
    assert rec is not None
    assert records.parse_refs(rec.get("Evidence")) == ["D-024", "D-037", "S-001"]
    assert records.parse_refs(rec.get("Features")) == ["F-001", "F-004", "F-008"]
    assert rec.get("Confidence") == "CONFIRMED"  # non-union fields are kept
    assert report.ignored_prose_lines > 0  # the staged steps are not merged into W-001


def test_two_new_workflows_get_consecutive_ids(tasklet_product_model: Path) -> None:
    ws = tasklet_product_model
    report = merge.merge(
        ws,
        stage(
            ws,
            {
                "research/workflows/b.md": BODY.format(
                    name="Export a board", evidence="D-037"
                ).replace("- U-?1\n", "- None yet.\n"),
                "research/workflows/a.md": BODY.format(name="Import tasks", evidence="D-037")
                .replace("W-?1", "W-?2")
                .replace("- U-?1\n", "- None yet.\n"),
            },
        ),
    )
    assert sorted(report.new_ids) == ["W-009", "W-010"]
    names = sorted(p.name for p in workflows.workflow_files(ws))[-2:]
    assert names == sorted(
        f"{report.id_map[k]}-{slug}.md"
        for k, slug in (("W-?1", "export-a-board"), ("W-?2", "import-tasks"))
    )
