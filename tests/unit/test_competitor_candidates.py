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
