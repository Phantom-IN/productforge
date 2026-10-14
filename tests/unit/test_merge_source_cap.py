from __future__ import annotations

from pathlib import Path

from pflib import config, merge, metrics, workspace


def src(pid: str, n: int) -> str:
    url = f"https://docs.tasklet.example/new-{n}"
    return (
        f"### {pid} — New page {n}\n- URL: {url}\n- Canonical URL: {url}\n- Category: docs\n"
        "- Tier: 1\n- Authority: High\n- Relevant area: Tasks\n- Published: unknown\n"
        "- Last inspected: 2026-10-08\n- Notes:\n"
    )


def stage(ws: Path, files: dict[str, str]) -> str:
    run_id, path = workspace.create_staging_run(ws, "research-agent")
    for rel, text in files.items():
        (path / rel).parent.mkdir(parents=True, exist_ok=True)
        (path / rel).write_text(text)
    return run_id


def test_cap_drops_unreferenced_new_sources_last_first(tasklet_discovery: Path) -> None:
    config.write_config(tasklet_discovery, {"research.max_sources": 22})  # fixture has 20
    sources = "\n".join(src(f"S-?{i}", i) for i in range(1, 5))
    run = stage(tasklet_discovery, {"research/sources.md": sources})
    report = merge.merge(tasklet_discovery, run)
    assert report.dropped == ["S-?3", "S-?4"] and report.over_cap == 0
    assert report.added == {"S": 2}
    assert metrics.counts(tasklet_discovery)["S"] == 22


def test_cited_sources_are_kept_over_the_cap(tasklet_discovery: Path) -> None:
    config.write_config(tasklet_discovery, {"research.max_sources": 20})
    overview = "## Coverage\n\n- docs: S-?2\n"
    run = stage(tasklet_discovery, {
        "research/sources.md": src("S-?1", 1) + "\n" + src("S-?2", 2),
        "research/product-overview.md": overview,
    })  # fmt: skip
    report = merge.merge(tasklet_discovery, run)
    assert report.dropped == ["S-?1"] and report.over_cap == 1
    assert report.id_map == {"S-?2": "S-021"}


def test_dedupes_do_not_count_against_the_cap(tasklet_discovery: Path) -> None:
    config.write_config(tasklet_discovery, {"research.max_sources": 20})
    existing = (
        "### S-?1 — Docs again\n- URL: https://docs.tasklet.example/tasks\n"
        "- Canonical URL: https://docs.tasklet.example/tasks\n- Category: docs\n- Tier: 1\n"
        "- Authority: High\n- Relevant area: Tasks\n- Published: unknown\n"
        "- Last inspected: 2026-10-08\n- Notes:\n"
    )
    report = merge.merge(tasklet_discovery, stage(tasklet_discovery,
                                                  {"research/sources.md": existing}))  # fmt: skip
    assert report.dropped == [] and report.deduped == 1


def test_a_run_without_new_sources_reports_no_excess(tasklet_discovery: Path) -> None:
    config.write_config(tasklet_discovery, {"research.max_sources": 5})  # already 20 sources
    claim = (
        "### D-?1 — Boards can be filtered by assignee\n- Claim: A board filters by assignee.\n"
        "- Evidence: S-001\n- Confidence: CONFIRMED\n- Product impact:\n- Engineering impact:\n"
        "- Status: active\n"
    )
    run = stage(tasklet_discovery, {"research/DISCOVERY_LEDGER.md": claim})
    report = merge.merge(tasklet_discovery, run)
    assert report.over_cap == 0 and report.dropped == []
