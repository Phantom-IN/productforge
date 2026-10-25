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


def test_next_candidates_by_rank_and_company_pages_excluded(tasklet_discovery: Path) -> None:
    def ranked_entry(name: str, rank: int, hits: int = 0, nav: bool = False) -> dict:
        e = entry(f"https://tasklet.example/docs/{name}", "docs")
        return e | {"rank": rank, "scope_hits": hits, "nav": nav}

    entries = [ranked_entry(f"p{i}", 100 + i) for i in range(30)]
    entries += [ranked_entry("hit", 500, hits=2), ranked_entry("nav", 900, nav=True)]
    entries += [entry("https://tasklet.example/about", "company")]
    entries += [entry("https://docs.tasklet.example/tasks", "docs")]  # already S-001
    write_cache(tasklet_discovery, entries)
    cache = workspace.pf_dir(tasklet_discovery) / workspace.CACHE / "discover/tasklet.example.json"
    data = json.loads(cache.read_text()) | {"truncated": 7}
    cache.write_text(json.dumps(data))
    plan = research.plan(tasklet_discovery)
    docs = {p["name"]: p for p in plan["partitions"]}["official-docs"]
    nxt = docs["next_candidates"]
    assert len(nxt) == 20 and nxt[:3] == [
        "https://tasklet.example/docs/nav",
        "https://tasklet.example/docs/hit",
        "https://tasklet.example/docs/p0",
    ]
    assert all("about" not in u and u != "https://docs.tasklet.example/tasks" for u in nxt)
    assert docs["candidates"] == 32 and plan["truncated"] == 7
    assert all(len(p["next_candidates"]) <= 20 for p in plan["partitions"])


def test_old_cache_without_rank_orders_by_url(tasklet_discovery: Path) -> None:
    write_cache(tasklet_discovery, [entry("https://tasklet.example/docs/b", "docs"),
                                    entry("https://tasklet.example/docs/a", "docs")])  # fmt: skip
    plan = research.plan(tasklet_discovery)
    docs = {p["name"]: p for p in plan["partitions"]}["official-docs"]
    assert docs["next_candidates"] == ["https://tasklet.example/docs/a",
                                       "https://tasklet.example/docs/b"]  # fmt: skip
    assert plan["truncated"] == 0


def test_scope_terms_from_scope_areas_and_entities(
    tasklet_discovery: Path, edit_state: Callable[..., None]
) -> None:
    edit_state(scope={"text": "Task tracking for small teams", "source": "user",
                      "accepted": False})  # fmt: skip
    terms = research.scope_terms(tasklet_discovery)
    assert {"task", "track", "team", "board", "project", "notification", "workspace"} <= terms
    assert "with" not in terms and "for" not in terms and "S-001" not in terms
    assert not any(len(t) < 4 for t in terms)
    edit_state(scope={"text": None, "source": None, "accepted": False})
    assert "track" not in research.scope_terms(tasklet_discovery)
    assert research.slug_tokens("https://x.example/help/Filing-Cases/new") == {"help", "filing",
                                                                                "case"}  # fmt: skip
    assert research.plan(tasklet_discovery)["scope_terms"] == sorted(
        research.scope_terms(tasklet_discovery)
    )


# --- phase 01: depth, nav pages, unknown audit ---------------------------------------------


def scoped(url: str, hits: int = 1, nav: bool = False, rank: int = 1, cat: str = "docs") -> dict:
    return {**entry(url, cat), "scope_hits": hits, "nav": nav, "rank": rank}


def test_depth_arithmetic_and_exclusions(tasklet_discovery: Path) -> None:
    from pflib import exclusions

    ws = tasklet_discovery
    config.write_config(ws, {"research.max_excluded_share": 1.0})
    read = [f"https://docs.tasklet.example/p{i}" for i in range(40)]
    rest = [f"https://docs.tasklet.example/q{i}" for i in range(60)]
    write_cache(
        ws, [scoped(u) for u in read + rest] + [scoped("https://docs.tasklet.example/z", 0)]
    )
    d = research.depth(ws)
    assert d["in_scope"] == 100 and d["read"] == 0 and d["needed"] == 60
    exclusions.add(ws, read[:40], "off-scope")
    d = research.depth(ws)
    assert d["excluded"] == 40 and d["ratio"] == 0.4 and d["needed"] == 20
    exclusions.add(ws, rest[:20], "dupes")
    assert research.depth(ws)["needed"] == 0 and research.depth(ws)["ratio"] == 0.6
    plan = research.plan(ws)
    assert plan["depth_needed"] == 0 and plan["budget_needed"] == 0


def test_depth_without_candidates_is_vacuous(tasklet_discovery: Path) -> None:
    assert research.depth(tasklet_discovery)["ratio"] == 1.0
    assert research.depth(tasklet_discovery)["needed"] == 0


def test_budget_needed_and_nav_first(tasklet_discovery: Path) -> None:
    ws = tasklet_discovery
    config.write_config(ws, {"research.max_sources": 21})  # 1 remaining
    write_cache(
        ws,
        [scoped(f"https://tasklet.example/p{i}", 2, rank=i + 1) for i in range(10)]
        + [scoped("https://tasklet.example/nav", 0, nav=True, rank=99, cat="features")],
    )
    plan = research.plan(ws)
    assert plan["depth_needed"] == 7 and plan["budget_needed"] == 6
    assert plan["nav_unread"] == ["https://tasklet.example/nav"]
    core = next(p for p in plan["partitions"] if p["name"] == "official-core")
    assert core["next_candidates"][0] == "https://tasklet.example/nav"
    # non-official or disallowed entries never count
    write_cache(
        ws,
        [
            scoped("https://x.example/a", cat="reddit"),
            {**scoped("https://tasklet.example/b"), "allowed": False},
        ],
    )
    assert research.depth(ws)["in_scope"] == 0


def test_unknown_audit_two_token_rule_limit_and_exclusion(tasklet_discovery: Path) -> None:
    from pflib import exclusions

    ws = tasklet_discovery  # U-001: "How long does the product keep task activity history?"
    hits = [f"https://docs.tasklet.example/task-history-{i}" for i in range(7)]
    write_cache(
        ws,
        [scoped(u, 0, rank=i + 1) for i, u in enumerate(hits)]
        + [
            scoped("https://docs.tasklet.example/history", 0, rank=20),
            scoped("https://docs.tasklet.example/unrelated-billing", 0, rank=21),
        ],
    )
    audit = research.unknown_audit(ws)
    assert audit["U-001"] == hits[:5]  # at most 5; one-token and unrelated slugs never match
    exclusions.add(ws, hits[:3], "dupes")
    assert research.unknown_audit(ws)["U-001"] == hits[3:7]
    exclusions.add(ws, hits[3:], "dupes")
    assert "U-001" not in research.unknown_audit(ws)
