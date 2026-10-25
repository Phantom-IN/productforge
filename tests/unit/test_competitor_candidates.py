from __future__ import annotations

import json
from pathlib import Path

from pflib import competitors, config, records


def drop_competitors(ws: Path) -> None:
    p = ws / "research/COMPETITORS.md"
    p.write_text(p.read_text().split("\n## Records\n")[0] + "\n## Records\n\n## Feature signals\n")


def test_names_come_from_comparison_titles_only(tasklet_product_model: Path) -> None:
    drop_competitors(tasklet_product_model)
    result = competitors.candidates(tasklet_product_model)
    assert result["candidates"] == ["Doable", "Listwise", "Taskmate"]  # target name left out
    assert result["evidence"] == {"Doable": ["S-021"], "Listwise": ["S-022"], "Taskmate": ["S-021"]}
    assert result["cap"] == 5 and result["existing"] == []
    assert result["category"].startswith("Work management")
    assert competitors.candidates(tasklet_product_model) == result  # deterministic


def test_recorded_competitors_and_the_cap(tasklet_product_model: Path) -> None:
    assert competitors.candidates(tasklet_product_model)["candidates"] == []  # all recorded
    drop_competitors(tasklet_product_model)
    config.write_config(tasklet_product_model, {"competitors.max": 2})
    result = competitors.candidates(tasklet_product_model)
    assert result["candidates"] == ["Doable", "Listwise"] and result["more"] == ["Taskmate"]


def test_name_extraction() -> None:
    names = competitors._names_in  # noqa: SLF001
    assert names("Tasklet vs Taskmate vs Doable for small teams") == [
        "Tasklet",
        "Taskmate",
        "Doable",
    ]
    assert names("The Best Listwise Alternatives in 2026") == ["Listwise"]
    assert names("Review for small teams") == []
    assert records.normalise_text("Tasklet") == records.normalise_text("tasklet")


def test_cli(pf_cli, tasklet_product_model: Path) -> None:  # type: ignore[no-untyped-def]
    drop_competitors(tasklet_product_model)
    code, out, _ = pf_cli(
        "competitor-candidates", "--workspace", str(tasklet_product_model), "--json"
    )
    assert code == 0 and json.loads(out)["candidates"] == ["Doable", "Listwise", "Taskmate"]


def _add_source(ws: Path, sid: str, title: str, url: str, category: str) -> None:
    block = (
        f"\n### {sid} — {title}\n- URL: {url}\n- Canonical URL: {url}\n- Category: {category}\n"
        "- Tier: 4\n- Authority: Low\n- Relevant area: Comparison\n- Published: unknown\n"
        "- Last inspected: 2026-10-08\n- Notes: n\n"
    )
    p = ws / "research/sources.md"
    p.write_text(p.read_text(encoding="utf-8") + block, encoding="utf-8")


def test_aggregators_and_generic_words_are_not_candidates(tasklet_product_model: Path) -> None:
    ws = tasklet_product_model
    drop_competitors(ws)
    _add_source(ws, "S-901", "Tasklet Alternatives: AlternativeTo", "https://alternativeto.net/x",
                "comparison-articles")  # fmt: skip
    _add_source(ws, "S-902", "OSSAlt and G2 pick the URL tool", "https://ossalt.example/y",
                "comparison-articles")  # fmt: skip
    _add_source(ws, "S-903", "Reviews of Tasklet", "https://www.g2.com/products/tasklet",
                "docs")  # fmt: skip
    result = competitors.candidates(ws)
    for bad in ("AlternativeTo", "OSSAlt", "G2", "URL"):
        assert bad not in result["candidates"] and bad not in result["more"]
    assert {"S-901", "S-902", "S-903"} <= set(result["comparison_sources"])
    assert {"Doable", "Listwise", "Taskmate"} <= set(result["candidates"])
    assert result["min_researched"] == 2


def test_aggregator_list_is_configurable(tasklet_product_model: Path) -> None:
    ws = tasklet_product_model
    drop_competitors(ws)
    config.write_config(ws, {"competitors.aggregator_names": ["Doable"]})
    assert "Doable" not in competitors.candidates(ws)["candidates"]
