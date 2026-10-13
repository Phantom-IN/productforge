from __future__ import annotations

from pathlib import Path

from pflib import merge, workspace
from pflib.merge import merge_keyed_block

OVERVIEW = "research/product-overview.md"


def stage(ws: Path, text: str) -> str:
    run_id, path = workspace.create_staging_run(ws, "research-agent")
    (path / "research").mkdir()
    (path / OVERVIEW).write_text(text)
    return run_id


def test_keyed_block_merge() -> None:
    canon = "## Coverage\n\nIntro.\n\n- docs: S-001\n- pricing: S-006\n\nNote.\n"
    staged = "## Coverage\n\n- pricing: S-006, S-021\n- forums: S-030\n"
    assert merge_keyed_block(canon, staged) == (
        "## Coverage\n\nIntro.\n\n- docs: S-001\n- pricing: S-006, S-021\n"
        "- forums: S-030\n\nNote.\n"
    )


def test_parallel_runs_keep_each_others_coverage_lines(tasklet_discovery: Path) -> None:
    ws = tasklet_discovery
    first = stage(ws, "## Coverage\n\n- forums: S-010\n")
    second = stage(ws, "## Coverage\n\n- review-sites: S-012\n")
    merge.merge(ws, first)
    merge.merge(ws, second)
    body = (ws / OVERVIEW).read_text().split("## Coverage", 1)[1].split("\n## ", 1)[0]
    assert "- forums: S-010\n" in body and "- review-sites: S-012\n" in body
    assert "- docs:" in body  # untouched canonical lines survive


def test_other_sections_still_replace(tasklet_discovery: Path) -> None:
    ws = tasklet_discovery
    merge.merge(ws, stage(ws, "## Target users\n\nSmall teams and agencies (S-007).\n"))
    text = (ws / OVERVIEW).read_text()
    body = text.split("## Target users", 1)[1].split("\n## ", 1)[0]
    assert body.strip() == "Small teams and agencies (S-007)."
