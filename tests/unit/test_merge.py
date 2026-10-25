from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pflib import merge, records, workspace
from pflib.errors import PFError
from pflib.merge import MergeError


def source(pid: str, title: str, url: str, tier: str = "1", notes: str = "n") -> str:
    return (
        f"### {pid} — {title}\n- URL: {url}\n- Canonical URL: {url}\n- Category: docs\n"
        f"- Tier: {tier}\n- Authority: High\n- Relevant area: Tasks\n- Published: unknown\n"
        f"- Last inspected: 2026-10-08\n- Notes: {notes}\n"
    )


def claim(pid: str, text: str, evidence: str, confidence: str = "CONFIRMED") -> str:
    return (
        f"### {pid} — {text}\n- Claim: {text}\n- Evidence: {evidence}\n- Confidence: {confidence}\n"
        "- Product impact:\n- Engineering impact:\n- Status: active\n"
    )


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    (tmp_path / ".productforge").mkdir()
    return tmp_path


def stage(ws: Path, files: dict[str, str], role: str = "research-agent") -> str:
    run_id, path = workspace.create_staging_run(ws, role)
    for rel, text in files.items():
        target = path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return run_id


def tree_hash(ws: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(ws.rglob("*")):
        if p.is_file() and ".productforge" not in p.parts:
            h.update(p.relative_to(ws).as_posix().encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def test_new_records_get_sequential_ids_and_refs_are_rewritten(ws: Path) -> None:
    run = stage(
        ws,
        {
            "research/sources.md": source("S-?1", "Docs", "https://docs.tasklet.example/a")
            + "\n"
            + source("S-?2", "Help", "https://help.tasklet.example/b"),
            "research/DISCOVERY_LEDGER.md": claim("D-?1", "Tasks can have labels", "S-?2, S-?1"),
        },
    )
    report = merge.merge(ws, run)
    assert report.added == {"D": 1, "S": 2}
    assert report.id_map == {"D-?1": "D-001", "S-?1": "S-001", "S-?2": "S-002"}
    ledger = records.parse_document((ws / "research/DISCOVERY_LEDGER.md").read_text())
    assert ledger.records[0].get("Evidence") == "S-002, S-001"
    assert ledger.records[0].section == "Records"
    assert "?" not in (ws / "research/sources.md").read_text()


def test_second_run_continues_numbering(ws: Path) -> None:
    merge.merge(ws, stage(ws, {"research/sources.md": source("S-?1", "A", "https://a.example/1")}))
    report = merge.merge(
        ws, stage(ws, {"research/sources.md": source("S-?1", "B", "https://b.example/2")})
    )
    assert report.id_map == {"S-?1": "S-002"}
    doc = records.parse_document((ws / "research/sources.md").read_text())
    assert [r.id for r in doc.records] == ["S-001", "S-002"]


def test_dedupe_by_canonical_url_unions_evidence_and_allocates_nothing(ws: Path) -> None:
    merge.merge(
        ws,
        stage(
            ws,
            {
                "research/sources.md": source("S-?1", "Docs", "https://docs.tasklet.example/a")
                + "\n"
                + source("S-?2", "Blog", "https://tasklet.example/blog/x"),
                "research/DISCOVERY_LEDGER.md": claim("D-?1", "Tasks can have labels", "S-?1"),
            },
        ),
    )
    # Run 2: re-discovers the same docs page and the same (differently worded) claim.
    report = merge.merge(
        ws,
        stage(
            ws,
            {
                "research/sources.md": source(
                    "S-?1", "Docs (again)", "https://docs.tasklet.example/a"
                ),
                "research/DISCOVERY_LEDGER.md": claim(
                    "D-?1", "Tasks can have Labels.", "S-?1, S-002"
                ),
            },
        ),
    )
    assert report.added == {}
    assert report.deduped == 2
    assert report.id_map == {"D-?1": "D-001", "S-?1": "S-001"}
    ledger = records.parse_document((ws / "research/DISCOVERY_LEDGER.md").read_text())
    assert len(ledger.records) == 1
    assert ledger.records[0].get("Evidence") == "S-001, S-002"
    sources = records.parse_document((ws / "research/sources.md").read_text())
    assert [r.id for r in sources.records] == ["S-001", "S-002"]
    assert sources.records[0].title == "Docs"  # canonical kept


def test_two_runs_citing_same_new_source_in_one_run_collapse(ws: Path) -> None:
    report = merge.merge(
        ws,
        stage(
            ws,
            {
                "research/sources.md": source("S-?1", "Docs", "https://x.example/a")
                + "\n"
                + source("S-?2", "Docs dup", "https://x.example/a"),
                "research/DISCOVERY_LEDGER.md": claim("D-?1", "Claim one", "S-?1")
                + "\n"
                + claim("D-?2", "Claim two", "S-?2"),
            },
        ),
    )
    assert report.added == {"D": 2, "S": 1}
    assert report.id_map["S-?2"] == report.id_map["S-?1"] == "S-001"
    ledger = records.parse_document((ws / "research/DISCOVERY_LEDGER.md").read_text())
    assert [r.get("Evidence") for r in ledger.records] == ["S-001", "S-001"]


def test_conflicting_non_union_fields_are_reported_not_applied(ws: Path) -> None:
    merge.merge(
        ws,
        stage(ws, {"research/sources.md": source("S-?1", "Docs", "https://x.example/a", tier="1")}),
    )
    report = merge.merge(
        ws,
        stage(ws, {"research/sources.md": source("S-?1", "Docs", "https://x.example/a", tier="3")}),
    )
    assert {"id": "S-001", "field": "Tier", "kept": "1", "staged": "3"} in report.conflicts
    assert "- Tier: 1" in (ws / "research/sources.md").read_text()


def test_dangling_provisional_aborts_and_touches_nothing(ws: Path) -> None:
    merge.merge(
        ws, stage(ws, {"research/sources.md": source("S-?1", "Docs", "https://x.example/a")})
    )
    before = tree_hash(ws)
    marks_before = workspace.load_id_marks(ws)
    run = stage(
        ws,
        {
            "research/sources.md": source("S-?1", "New", "https://y.example/b"),
            "research/DISCOVERY_LEDGER.md": claim("D-?1", "Claim", "S-?1, S-?9"),
        },
    )
    with pytest.raises(MergeError) as info:
        merge.merge(ws, run)
    assert info.value.code == "DANGLING_PROVISIONAL"
    assert info.value.details["ids"] == ["S-?9"]
    assert tree_hash(ws) == before
    assert workspace.load_id_marks(ws) == marks_before
    assert workspace.staging_dir(ws, run).is_dir()  # not archived
    assert not (ws / ".productforge" / workspace.MERGE_LOCK).exists()


def test_workflow_record_file_gets_final_name(ws: Path) -> None:
    body = (
        "### W-?1 — Create task\n- Actor: Member\n- Trigger: Clicks New\n- Features: F-001\n"
        "- Surfaces: PS-01\n- Evidence: S-001\n- Confidence: PROBABLE\n- Preconditions:\n"
        "- Outcome: Task exists\n\n## Steps\n1. [observed] User opens composer — S-001\n"
        "2. [implied-system] Task persisted\n\nSee also W-?1.\n"
    )
    report = merge.merge(
        ws, stage(ws, {"research/workflows/create-task.md": body}, role="ux-analyst")
    )
    assert report.files_written == ["research/workflows/W-001-create-task.md"]
    text = (ws / "research/workflows/W-001-create-task.md").read_text()
    assert text.startswith("### W-001 — Create task\n")
    assert "## Steps\n1. [observed]" in text and "See also W-001." in text


def test_history_and_archive(ws: Path) -> None:
    run = stage(ws, {"research/sources.md": source("S-?1", "Docs", "https://x.example/a")})
    merge.merge(ws, run)
    events = [e["event"] for e in workspace.read_history(ws)]
    assert events[-2:] == ["staging-new", "merge"]
    last = workspace.read_history(ws)[-1]
    assert last["run_id"] == run and last["added"] == {"S": 1}
    assert (ws / ".productforge/staging/_merged" / run).is_dir()
    assert not workspace.staging_dir(ws, run).exists()
    with pytest.raises(PFError) as info:
        merge.merge(ws, run)
    assert info.value.code == "NO_SUCH_RUN"


@pytest.mark.parametrize(
    "files, code",
    [
        ({"research/sources.md": source("S-001", "Final", "https://x.example")}, "STAGED_FINAL_ID"),
        ({"research/sources.md": claim("D-?1", "Wrong file", "S-001")}, "WRONG_ARTIFACT"),
        ({"research/nope.md": "# x\n"}, "UNKNOWN_ARTIFACT"),
        ({"research/workflows/two.md": "### W-?1 — a\n\n### W-?2 — b\n"}, "BAD_RECORD_FILE"),
        (
            {
                "research/sources.md": source("S-?1", "A", "https://a.example"),
                "research/UNKNOWNS.md": "### S-?1 — dup\n",
            },
            "WRONG_ARTIFACT",
        ),
    ],
)
def test_refusals(ws: Path, files: dict[str, str], code: str) -> None:
    before = tree_hash(ws)
    with pytest.raises(MergeError) as info:
        merge.merge(ws, stage(ws, files))
    assert info.value.code == code
    assert tree_hash(ws) == before


def test_duplicate_provisional_across_files(ws: Path) -> None:
    run = stage(
        ws,
        {
            "research/DISCOVERY_LEDGER.md": claim("D-?1", "A", "S-001"),
            "research/workflows/x.md": "### W-?1 — a\n- Evidence: D-?1\n",
            "research/workflows/y.md": "### W-?1 — b\n",
        },
    )
    with pytest.raises(MergeError) as info:
        merge.merge(ws, run)
    assert info.value.code == "DUPLICATE_ID"


def test_raw_and_dotfiles_are_ignored(ws: Path) -> None:
    report = merge.merge(
        ws,
        stage(
            ws,
            {
                "raw/deep-research-report.md": "### S-?99 — not merged\n",
                "research/sources.md": "Prose the agent added.\n\n"
                + source("S-?1", "A", "https://a.example"),
            },
        ),
    )
    assert report.added == {"S": 1}
    assert report.ignored_prose_lines == 1


def test_merge_lock_blocks_concurrent_merge(ws: Path) -> None:
    run = stage(ws, {"research/sources.md": source("S-?1", "A", "https://a.example")})
    (ws / ".productforge" / workspace.MERGE_LOCK).write_text("123")
    with pytest.raises(MergeError) as info:
        merge.merge(ws, run)
    assert info.value.code == "MERGE_LOCKED"


def test_ids_never_reused_even_if_top_record_vanishes(ws: Path) -> None:
    merge.merge(
        ws,
        stage(
            ws,
            {
                "research/sources.md": source("S-?1", "A", "https://a.example")
                + "\n"
                + source("S-?2", "B", "https://b.example")
            },
        ),
    )
    (ws / "research/sources.md").write_text("# Sources\n")  # simulate loss of records
    report = merge.merge(
        ws, stage(ws, {"research/sources.md": source("S-?1", "C", "https://c.example")})
    )
    assert report.id_map == {"S-?1": "S-003"}
    assert json.loads((ws / ".productforge/ids.json").read_text()) == {"S": 3}


def test_dedupe_keyed_on_refs_resolves_new_targets_first(ws: Path) -> None:
    feature = (
        "### F-?1 — Labels\n- Domain: Tasks\n- Feature: Labels\n- Parent:\n- Surface: PS-01\n"
        "- Evidence: D-001\n- Confidence: CONFIRMED\n- Plan tier: all\n- Complexity: Low\n"
        "- Notes:\n"
    )
    signal = (
        "### FS-?{n} — Labels table stakes\n- Feature: F-?1\n- Signal: table-stakes\n"
        "- Competitors: C-0{n}\n- Evidence: S-001\n- Notes:\n"
    )
    report = merge.merge(
        ws,
        stage(
            ws,
            {
                "research/COMPETITORS.md": signal.format(n=1) + "\n" + signal.format(n=2),
                "research/FEATURE_MATRIX.md": feature,
            },
        ),
    )
    assert report.added == {"F": 1, "FS": 1}
    doc = records.parse_document((ws / "research/COMPETITORS.md").read_text())
    (fs,) = doc.records
    assert fs.get("Feature") == "F-001" and fs.get("Competitors") == "C-01, C-02"
    assert fs.section == "Feature signals"


def test_document_sections_merge(ws: Path) -> None:
    (ws / "research").mkdir()
    (ws / "research/product-overview.md").write_text(
        "# Product overview\n\n## Product\n\nTBD\n\n## Coverage\n\nnone\n"
    )
    report = merge.merge(
        ws,
        stage(
            ws,
            {
                "research/product-overview.md": (
                    "## Product\n\nTasklet is a task tracker (S-?1).\n\n## Category\n\nTasks\n"
                ),
                "research/sources.md": source("S-?1", "A", "https://a.example"),
            },
        ),
    )
    assert report.documents_updated == ["research/product-overview.md"]
    assert (ws / "research/product-overview.md").read_text() == (
        "# Product overview\n\n## Product\n\nTasklet is a task tracker (S-001).\n\n"
        "## Coverage\n\nnone\n\n## Category\n\nTasks\n"
    )


def test_allocate_next_reserves_ids(ws: Path) -> None:
    assert merge.allocate_next(ws, "D") == "D-001"
    assert merge.allocate_next(ws, "D") == "D-002"
    report = merge.merge(
        ws, stage(ws, {"research/DISCOVERY_LEDGER.md": claim("D-?1", "X", "S-001")})
    )
    assert report.id_map == {"D-?1": "D-003"}


# ---- input receipts (v3 phase 06) --------------------------------------------------------


def _receipt_run(ws: Path, inputs: list[str]) -> str:
    from pflib import receipts

    run_id, run_dir = workspace.create_staging_run(ws, "systems-architect")
    receipts.save_inputs(run_dir, inputs)
    return run_id


def _codes(result: dict) -> list[tuple[str, str]]:
    return [
        (f["code"], f["artifact"]) for f in result["findings"] if f["code"].startswith("INPUT_")
    ]


def test_short_receipt_reports_both_numbers(tasklet_scope: Path) -> None:
    run_id = _receipt_run(tasklet_scope, ["spec/PRODUCT_SPEC.md"])
    summary = tasklet_scope / "reply.txt"
    summary.write_text("RUN x · ROLE y\nREAD spec/PRODUCT_SPEC.md: 1\n", encoding="utf-8")
    result = merge.preflight(tasklet_scope, run_id, summary)
    (f,) = [f for f in result["findings"] if f["code"] == "INPUT_RECEIPT_SHORT"]
    real = (tasklet_scope / "spec/PRODUCT_SPEC.md").read_text(encoding="utf-8").count("\n### R-")
    assert f["severity"] == "warn" and f["artifact"] == "spec/PRODUCT_SPEC.md"
    assert "READ spec/PRODUCT_SPEC.md: 1" in f["message"] and f"holds {real}" in f["message"]
    assert result["ok"] is True and result["warnings"] >= 1


def test_missing_receipt_and_no_summary_at_all(tasklet_scope: Path) -> None:
    run_id = _receipt_run(tasklet_scope, ["spec/PRODUCT_SPEC.md", "spec/DOMAIN_MODEL.md"])
    summary = tasklet_scope / "reply.txt"
    full = (tasklet_scope / "spec/PRODUCT_SPEC.md").read_text(encoding="utf-8").count("\n### R-")
    summary.write_text(f"READ spec/PRODUCT_SPEC.md: {full}\n", encoding="utf-8")
    result = merge.preflight(tasklet_scope, run_id, summary)
    assert _codes(result) == [("INPUT_RECEIPT_MISSING", "spec/DOMAIN_MODEL.md")]
    none = merge.preflight(tasklet_scope, run_id)  # no SUMMARY.md saved
    assert [c for c, _ in _codes(none)] == ["INPUT_RECEIPT_MISSING"] * 2


def test_full_receipts_give_no_warning_and_staging_summary_is_read(tasklet_scope: Path) -> None:
    run_id = _receipt_run(tasklet_scope, ["spec/PRODUCT_SPEC.md"])
    full = (tasklet_scope / "spec/PRODUCT_SPEC.md").read_text(encoding="utf-8").count("\n### R-")
    run_dir = workspace.staging_dir(tasklet_scope, run_id)
    # absolute paths and 90 % of the count are accepted; SUMMARY.md is never merged
    n = -(-full * 9 // 10)  # ceil(0.9 * full)
    (run_dir / "SUMMARY.md").write_text(
        f"READ {tasklet_scope}/spec/PRODUCT_SPEC.md: {n}\n", encoding="utf-8"
    )
    result = merge.preflight(tasklet_scope, run_id)
    assert _codes(result) == [] and result["merge_error"] is None
    assert workspace.pending_runs(tasklet_scope)[0]["files"] == 0


def test_runs_without_recorded_inputs_have_no_receipt_findings(tasklet_discovery: Path) -> None:
    run_id, _ = workspace.create_staging_run(tasklet_discovery, "research-agent")
    assert _codes(merge.preflight(tasklet_discovery, run_id)) == []


def test_new_competitors_merge_after_product_model_closed(tasklet_scope: Path) -> None:
    ws = tasklet_scope
    comp = (
        "### C-?1 — Zipboard\n- Name: Zipboard\n- URL: https://zipboard.example/\n"
        "- Positioning: Boards\n- Target users: Teams\n- Pricing model: Free\n"
        "- Table-stakes features: F-001\n- Differentiators: None\n- Common complaints: None\n"
        "- Evidence: S-023\n- Confidence: CONFIRMED\n"
    )
    run = stage(ws, {"research/COMPETITORS.md": "## Records\n\n" + comp
                     + "\n## Feature signals\n\n"
                     "### FS-?1 — Tasks is rare\n- Feature: F-002\n- Signal: rare\n"
                     "- Competitors: C-?1\n- Evidence: S-023\n- Notes:\n"})  # fmt: skip
    report = merge.merge(ws, run)
    assert any(i.startswith("C-") for i in report.new_ids)
    assert any(i.startswith("FS-") for i in report.new_ids)
    from pflib import validators

    assert not [f for f in validators.run(ws) if f.code.startswith("LOCK_")]
