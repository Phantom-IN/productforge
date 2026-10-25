"""Research planning — ``pf.py research-plan``.

Scripts do the arithmetic: which categories are covered, how many candidate URLs each research
partition has, how the remaining source budget is split, and whether the user must be asked to
narrow the scope before more research happens.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from pflib import catalog, config, discover, exclusions, metrics, records, state, taxonomy, urls
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
UNPARTITIONED = ("unverified", "provider-report", "observed-session", "company")  # never researched
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


STOP_WORDS = frozenset(
    {
        "about", "also", "and", "are", "area", "areas", "between", "does", "each", "for", "from",
        "have", "into", "just", "like", "more", "most", "only", "other", "over", "that", "the",
        "their", "them", "then", "there", "these", "they", "this", "those", "through", "using",
        "very", "what", "when", "where", "which", "while", "will", "with", "within", "without",
        "your",
    }
)  # fmt: skip
_RECORD_ID = re.compile(r"\b[A-Z]{1,3}-\??\d+\b")
NEXT_CANDIDATES = 20
_NO_RANK = 10**9  # entries of older caches (no rank) sort after ranked ones


slug_tokens = urls.slug_tokens


def scope_terms(ws: Path) -> set[str]:
    """Lowercase stemmed words of the scope text, ``Major areas`` and domain entity names."""
    text = [str(state.load(ws).scope.get("text") or "")]
    text.extend(major_areas(ws))
    path = ws / catalog.DOMAIN_MODEL_PATH
    if path.is_file():
        doc = records.parse_document(path.read_text(encoding="utf-8"))
        text.extend(rec.title for rec in doc.records if rec.prefix == "E")
    return urls.tokens(_RECORD_ID.sub(" ", " ".join(text))) - STOP_WORDS


def read_urls(ws: Path, index: WorkspaceIndex | None = None) -> set[str]:
    """Canonical URLs of the ``S`` records."""
    index = index or WorkspaceIndex(ws)
    return {rec.get("Canonical URL").strip() for _, rec in index.records("S")} - {""}


def read_keys(ws: Path, index: WorkspaceIndex | None = None) -> set[str]:
    """Page keys of the read sources (``www.host`` and ``host`` are one page)."""
    return {urls.page_key(u) for u in read_urls(ws, index)}


def _official_entries(ws: Path) -> list[dict[str, Any]]:
    """Allowed, official-category entries of the discovery caches, unique, best rank first."""
    seen: dict[str, dict[str, Any]] = {}
    for cache in discover.load_cache(ws):
        for e in cache.get("entries", []):
            cat = e.get("category")
            if e.get("allowed") is False or cat not in taxonomy.OFFICIAL or cat in UNPARTITIONED:
                continue
            cur = seen.get(e["canonical_url"])
            if cur is None or _rank_key(e) < _rank_key(cur):
                seen[e["canonical_url"]] = e
    return sorted(seen.values(), key=_rank_key)


def _rank_key(e: dict[str, Any]) -> tuple[bool, int, int, str]:
    return (
        not e.get("nav"),
        -int(e.get("scope_hits") or 0),
        int(e.get("rank") or _NO_RANK),
        e["canonical_url"],
    )


def in_scope_candidates(ws: Path) -> list[dict[str, Any]]:
    """Allowed official entries with ``scope_hits >= 1`` or a homepage-navigation link."""
    return [e for e in _official_entries(ws) if int(e.get("scope_hits") or 0) >= 1 or e.get("nav")]


def depth(ws: Path, index: WorkspaceIndex | None = None) -> dict[str, Any]:
    """``{in_scope, read, excluded, ratio, needed}``; ``needed`` = extra reads to reach the knob.

    Exclusions count toward depth only up to ``research.max_excluded_share`` of the in-scope
    candidates; ``excluded`` is the counted number, ``excluded_total`` all of them and
    ``excluded_uncounted`` the rest.
    """
    in_scope = {urls.page_key(e["canonical_url"]) for e in in_scope_candidates(ws)}
    read = in_scope & read_keys(ws, index)
    excluded_all = (in_scope & exclusions.keys(ws)) - read
    total = len(in_scope)
    share = float(config.resolve("research.max_excluded_share", ws))
    counted = min(len(excluded_all), math.floor(share * total + 1e-9))
    wanted = float(config.resolve("research.min_scope_depth", ws))
    handled = len(read) + counted
    return {
        "in_scope": total,
        "read": len(read),
        "excluded": counted,
        "excluded_total": len(excluded_all),
        "excluded_uncounted": len(excluded_all) - counted,
        "ratio": round(handled / total, 3) if total else 1.0,
        "needed": max(0, math.ceil(wanted * total - 1e-9) - handled),
    }


def nav_unread(ws: Path, index: WorkspaceIndex | None = None) -> list[str]:
    """Homepage-navigation pages on the target's own host that are neither read nor excluded."""
    target = urls.host_of(state.load(ws).product["target_url"]).removeprefix("www.")
    done = read_keys(ws, index) | exclusions.keys(ws)
    return [
        e["canonical_url"]
        for e in in_scope_candidates(ws)
        if e.get("nav")
        and urls.page_key(e["canonical_url"]) not in done
        and urls.host_of(e["canonical_url"]).removeprefix("www.") == target
    ]


UNKNOWN_AUDIT_URLS = 5
MIN_SHARED_TOKENS = 2


def unknown_audit(ws: Path, index: WorkspaceIndex | None = None) -> dict[str, list[str]]:
    """Active ``U`` → up to 5 unread, unexcluded candidates whose slug shares >= 2 tokens."""
    index = index or WorkspaceIndex(ws)
    done = read_keys(ws, index) | exclusions.keys(ws)
    candidates = [
        (e["canonical_url"], slug_tokens(e["canonical_url"]))
        for e in _official_entries(ws)
        if urls.page_key(e["canonical_url"]) not in done
    ]
    out: dict[str, list[str]] = {}
    for _, rec in index.records("U"):
        if not records.is_active(rec):
            continue
        words = urls.tokens(_RECORD_ID.sub(" ", rec.get("Question"))) - STOP_WORDS
        hits = [u for u, toks in candidates if len(toks & words) >= MIN_SHARED_TOKENS]
        if hits:
            out[rec.id] = hits[:UNKNOWN_AUDIT_URLS]
    return out


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


def _next_candidates(entries: list[dict[str, Any]]) -> list[str]:
    """Up to ``NEXT_CANDIDATES`` unique canonical URLs, best rank first (old caches: by URL)."""

    out: list[str] = []
    for entry in sorted(entries, key=_rank_key):
        if entry["canonical_url"] not in out:
            out.append(entry["canonical_url"])
        if len(out) == NEXT_CANDIDATES:
            break
    return out


def plan(ws: Path) -> dict[str, Any]:
    st = state.load(ws)
    index = WorkspaceIndex(ws)
    known = read_keys(ws, index) | exclusions.keys(ws)
    cited = {
        ref for _, rec in index.records("D") for ref in records.parse_refs(rec.get("Evidence"))
    }
    category_of = {rec.id: rec.get("Category").strip() for _, rec in index.records("S")}
    cov = coverage(ws, index)
    max_sources = int(config.resolve("research.max_sources", ws))
    sources = sum(len(v) for v in cov.values())
    remaining = max(0, max_sources - sources)

    caches = discover.load_cache(ws)
    pending: dict[str, list[dict[str, Any]]] = {name: [] for name in PARTITIONS}
    total_candidates = 0
    seen: set[str] = set()  # one candidate per canonical URL across caches, entries and external
    for cache in caches:
        for entry in cache.get("entries", []) + cache.get("external", []):
            if entry.get("allowed") is False or urls.page_key(entry["canonical_url"]) in known:
                continue
            if entry.get("category") in UNPARTITIONED or entry["canonical_url"] in seen:
                continue
            seen.add(entry["canonical_url"])
            total_candidates += 1
            for name, cats in PARTITIONS.items():
                if entry.get("category") in cats:
                    pending[name].append(entry)
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
            "next_candidates": _next_candidates(pending[name]),
            "budget": budget[name],
            "provider": deep if name == "external" else "builtin",
        }
        for name in PARTITIONS
    ]
    dep = depth(ws, index)
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
        "scope_terms": sorted(scope_terms(ws)),
        "depth": dep,
        "depth_needed": dep["needed"],
        "budget_needed": max(0, dep["needed"] - remaining),
        "unknown_audit": unknown_audit(ws, index),
        "nav_unread": nav_unread(ws, index),
        "truncated": sum(int(c.get("truncated") or 0) for c in caches),
        "recommend_scope": (not scope_ok) and bool(reasons),
        "scope_reasons": reasons,
        "needs_scope": not scope_ok,
    }
