from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from pflib import config, research, state, taxonomy, workspace


def test_partitions_cover_every_real_category_exactly_once() -> None:
    assigned = [c for cats in research.PARTITIONS.values() for c in cats]
    assert len(assigned) == len(set(assigned))
    assert set(assigned) | set(research.UNPARTITIONED) == set(taxonomy.BY_NAME)
    assert sum(research.SHARES.values()) == 100


@pytest.mark.parametrize(
    "remaining, candidates, expected",
    [
        (64, {"official-docs": 100, "official-core": 100, "external": 0},
         {"official-docs": 29, "official-core": 16, "external": 19}),
        (64, {"official-docs": 5, "official-core": 3, "external": 0},
         {"official-docs": 5, "official-core": 3, "external": 56}),
        (0, {"official-docs": 5, "official-core": 3, "external": 0},
         {"official-docs": 0, "official-core": 0, "external": 0}),
    ],
)  # fmt: skip
def test_budget_split(remaining: int, candidates: dict[str, int], expected: dict[str, int]) -> None:
    budget = research._split(remaining, candidates)
    assert budget == expected and sum(budget.values()) == remaining


def write_cache(ws: Path, entries: list[dict], external: list[dict] | None = None) -> None:
    d = workspace.pf_dir(ws) / workspace.CACHE / "discover"
    d.mkdir(parents=True, exist_ok=True)
    (d / "tasklet.example.json").write_text(
        json.dumps({"host": "tasklet.example", "entries": entries, "external": external or []})
    )


def entry(url: str, category: str | None, allowed: bool = True) -> dict:
    return {"url": url, "canonical_url": url, "category": category, "allowed": allowed}


def test_plan_on_fixture_without_discovery(tasklet_discovery: Path) -> None:
    plan = research.plan(tasklet_discovery)
    assert plan["discovered"] is False and plan["caches"] == []
    assert plan["sources"] == 20 and plan["remaining_budget"] == 60
    assert plan["covered"]["docs"] == ["S-001", "S-002", "S-016"]
    assert "official-repo" in plan["uncovered_official"]  # explained by U-004, not a source
    assert "integrations" not in plan["uncovered_official"]
    assert "docs" not in plan["uncovered_official"]
    assert plan["needs_scope"] is False and plan["recommend_scope"] is False


def test_plan_counts_only_new_allowed_candidates(tasklet_discovery: Path) -> None:
    write_cache(
        tasklet_discovery,
        [
            entry("https://docs.tasklet.example/tasks", "docs"),  # already S-001
            entry("https://docs.tasklet.example/labels", "docs"),
            entry("https://tasklet.example/admin", "docs", allowed=False),
            entry("https://tasklet.example/integrations/calendar", "integrations"),
            entry("https://tasklet.example/about", None),
        ],
        external=[{"url": "https://github.com/tasklet", "canonical_url": "https://github.com/tasklet",
                   "category": "official-repo", "fetched": False}],
    )  # fmt: skip
    plan = research.plan(tasklet_discovery)
    parts = {p["name"]: p for p in plan["partitions"]}
    assert parts["official-docs"]["candidates"] == 2  # labels + official repo link
    assert parts["official-core"]["candidates"] == 1
    assert parts["official-docs"]["budget"] == 2 and parts["official-core"]["budget"] == 1
    assert parts["external"]["budget"] == 60 - 3
    assert plan["caches"] == [".productforge/cache/discover/tasklet.example.json"]


def test_scope_recommendation(tasklet_discovery: Path, edit_state: Callable[..., None]) -> None:
    edit_state(scope={"text": None, "source": None, "accepted": False})
    plan = research.plan(tasklet_discovery)
    assert plan["needs_scope"] is True and plan["recommend_scope"] is False
    areas = "\n".join(f"- Area {i} (S-001)" for i in range(9))
    (tasklet_discovery / "research/product-overview.md").write_text(
        f"# Product overview\n\n## Major areas\n\n{areas}\n"
    )
    plan = research.plan(tasklet_discovery)
    assert plan["major_areas"] == 9 and plan["recommend_scope"] is True
    assert plan["scope_reasons"] == ["9 major areas (> 8)"]
    config.write_config(tasklet_discovery, {"research.max_sources": 2})
    write_cache(tasklet_discovery, [entry(f"https://tasklet.example/docs/{i}", "docs")
                                    for i in range(3)])  # fmt: skip
    plan = research.plan(tasklet_discovery)
    assert "3 candidate URLs (> research.max_sources=2)" in plan["scope_reasons"]
    edit_state(scope={"text": "tasks", "source": "user", "accepted": True})
    assert research.plan(tasklet_discovery)["recommend_scope"] is False


@pytest.fixture
def edit_state(tasklet_discovery: Path) -> Callable[..., None]:
    def edit(**changes: object) -> None:
        st = state.load(tasklet_discovery)
        for key, value in changes.items():
            setattr(st, key, value)
        state.save(tasklet_discovery, st)

    return edit


def test_unmined_sources_and_evidence_counts(tasklet_discovery: Path) -> None:
    plan = research.plan(tasklet_discovery)
    parts = {p["name"]: p for p in plan["partitions"]}
    # every fixture source is already cited by at least one claim
    assert parts["official-core"]["unmined"] == []
    assert parts["external"]["unmined"] == []
    assert plan["claims"] == 42 and plan["min_claims_gate"] == 40 and plan["surfaces"] == 7
    ledger = tasklet_discovery / "research/DISCOVERY_LEDGER.md"
    ledger.write_text(ledger.read_text().replace("- Evidence: S-019\n", "- Evidence: S-017\n"))
    assert research.plan(tasklet_discovery)["partitions"][1]["unmined"] == ["S-019"]
