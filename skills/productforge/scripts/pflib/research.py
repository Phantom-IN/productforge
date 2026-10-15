"""Research planning — ``pf.py research-plan``.

Scripts do the arithmetic: which categories are covered, how many candidate URLs each research
partition has, how the remaining source budget is split, and whether the user must be asked to
narrow the scope before more research happens.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pflib import catalog, config, discover, metrics, records, state, taxonomy
from pflib.index import WorkspaceIndex

# Parallel research partitions. Every taxonomy category except the two "never a real
# source" ones belongs to exactly one partition (a test enforces it).
PARTITIONS: dict[str, tuple[str, ...]] = {
    "official-core": (
        "homepage", "features", "pricing", "enterprise", "integrations", "product-blog",
        "official-demo", "official-talk", "official-tutorial",
    ),
    "official-docs": (
        "docs", "api-docs", "help-center", "changelog", "security", "status", "engineering-blog",
        "official-repo",
    ),
    "external": (
        "tutorials", "review-sites", "technical-blogs", "comparison-articles", "youtube",
        "talks-podcasts", "github", "product-hunt", "reddit", "forums", "social",
    ),
}  # fmt: skip
UNPARTITIONED = ("unverified", "provider-report", "observed-session")  # never researched
# Official categories the DISCOVERY coverage gate asks about (observed sessions are optional).
COVERAGE_OFFICIAL = tuple(c for c in taxonomy.OFFICIAL if c not in UNPARTITIONED)
SHARES = {"official-docs": 45, "official-core": 25, "external": 30}  # percent of remaining budget
SCOPE_AREA_LIMIT = 8  # more major areas than this → recommend a scope


def _overview_doc(ws: Path) -> records.Document | None:
    spec = catalog.spec_for_path(catalog.OVERVIEW_PATH)
    assert spec is not None
    path = ws / spec.path
    return records.parse_document(path.read_text(encoding="utf-8")) if path.is_file() else None


def major_areas(ws: Path) -> list[str]:
    doc = _overview_doc(ws)
    body = doc.section_text("Major areas") if doc else None
    if not body:
        return []
    return [
        line[2:].strip() for line in body.splitlines() if line.startswith("- ") and line[2:].strip()
    ]


def coverage(ws: Path, index: WorkspaceIndex | None = None) -> dict[str, list[str]]:
    """Category → source IDs, for every taxonomy category (empty list = uncovered)."""
    index = index or WorkspaceIndex(ws)
    out: dict[str, list[str]] = {c.name: [] for c in taxonomy.CATEGORIES}
    for _, rec in index.records("S"):
        category = rec.get("Category").strip()
        if category in out:
            out[category].append(rec.id)
    return out


def _split(remaining: int, candidates: dict[str, int]) -> dict[str, int]:
    """Split ``remaining`` by SHARES; official partitions never get more than their candidates;
    leftovers flow to external research (web search finds its own candidates), then docs."""
    budget = {name: remaining * pct // 100 for name, pct in SHARES.items()}
    budget["official-docs"] += remaining - sum(budget.values())
    spare = 0
    for name in ("official-docs", "official-core"):
        if budget[name] > candidates[name]:
            spare += budget[name] - candidates[name]
            budget[name] = candidates[name]
    budget["external"] += spare
    return budget


def plan(ws: Path) -> dict[str, Any]:
    st = state.load(ws)
    index = WorkspaceIndex(ws)
    known = {rec.get("Canonical URL").strip() for _, rec in index.records("S")}
    cited = {
        ref for _, rec in index.records("D") for ref in records.parse_refs(rec.get("Evidence"))
    }
    category_of = {rec.id: rec.get("Category").strip() for _, rec in index.records("S")}
    cov = coverage(ws, index)
    max_sources = int(config.resolve("research.max_sources", ws))
    sources = sum(len(v) for v in cov.values())
    remaining = max(0, max_sources - sources)

    caches = discover.load_cache(ws)
    pending: dict[str, list[str]] = {name: [] for name in PARTITIONS}
    total_candidates = 0
    for cache in caches:
        for entry in cache.get("entries", []) + cache.get("external", []):
            if entry.get("allowed") is False or entry["canonical_url"] in known:
                continue
            total_candidates += 1
            for name, cats in PARTITIONS.items():
                if entry.get("category") in cats:
                    pending[name].append(entry["canonical_url"])
    counts = {name: len(v) for name, v in pending.items()}
    budget = _split(remaining, counts)
    resolved = st.capabilities.get("resolved", {})
    deep = resolved.get("research.deep", {}).get("provider", "builtin")

    areas = major_areas(ws)
    scope_ok = bool(st.scope.get("text") and st.scope.get("accepted"))
    reasons = []
    if len(areas) > SCOPE_AREA_LIMIT:
        reasons.append(f"{len(areas)} major areas (> {SCOPE_AREA_LIMIT})")
    if total_candidates > max_sources:
        reasons.append(f"{total_candidates} candidate URLs (> research.max_sources={max_sources})")
    partitions = [
        {
            "name": name,
            "categories": list(PARTITIONS[name]),
            "uncovered": [c for c in PARTITIONS[name] if not cov[c]],
            "unmined": sorted(
                sid
                for sid, cat in category_of.items()
                if cat in PARTITIONS[name] and sid not in cited
            ),
            "candidates": counts[name],
            "budget": budget[name],
            "provider": deep if name == "external" else "builtin",
        }
        for name in PARTITIONS
    ]
    return {
        "discovered": bool(caches),
        "caches": [p.relative_to(ws).as_posix() for p in discover.cache_paths(ws)],
        "target_url": st.product["target_url"],
        "sources": sources,
        "max_sources": max_sources,
        "remaining_budget": remaining,
        "covered": {c: ids for c, ids in cov.items() if ids},
        "uncovered_official": [c for c in COVERAGE_OFFICIAL if not cov[c]],
        "partitions": partitions,
        "major_areas": len(areas),
        "claims": len(metrics.active_claims(ws, index)),
        "min_claims_gate": int(config.resolve("research.min_claims_gate", ws)),
        "surfaces": len(index.records("PS")),
        "scope": st.scope,
        "recommend_scope": (not scope_ok) and bool(reasons),
        "scope_reasons": reasons,
        "needs_scope": not scope_ok,
    }
