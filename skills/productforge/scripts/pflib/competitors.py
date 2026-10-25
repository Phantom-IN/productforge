"""Competitive research: candidates and feature signals.

Competitors are a *category* lens, never a second discovery: a shallow ``C-`` record per competitor
and ``FS-`` feature signals linking competitors to the target's features. Competitor sources are
ordinary ``S-`` records whose ``Relevant area`` is ``competitor:<C-ID>``; they may support C and FS
records only, never claims about the target.

Which target features a competitor offers is recorded on its C record (``Table-stakes features``,
one run per competitor). Scripts then count: a feature offered by at least two competitors is
**table stakes**, by exactly one **rare** (``offers``). FS records hold the judgment signals:

- ``differentiator``   — a competitor markets the feature as what sets it apart
- ``absent-in-target`` — competitors offer a capability the target lacks (``Feature`` is a name,
  not an F ID; informational input to "missing opportunities")
- ``table-stakes`` / ``rare`` — allowed explicitly too (validated: ≥ 2 / exactly 1 competitors);
  they add to the counts.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pflib import catalog, config, records, state
from pflib.index import WorkspaceIndex

SIGNALS = ("table-stakes", "differentiator", "rare", "absent-in-target")
ABSENT = "absent-in-target"
TABLE_STAKES_MIN = 2
AREA_PREFIX = "competitor:"
CANDIDATE_CATEGORIES = ("comparison-articles", "review-sites")

_NAME_RE = re.compile(r"[A-Z][\w.+&-]*(?:\s+[A-Z][\w.+&-]*){0,2}")
_STOP = {
    "a", "an", "the", "best", "top", "review", "reviews", "alternative", "alternatives",
    "compared", "comparison", "vs", "versus", "for", "and", "or", "with", "how", "why", "what",
    "which", "guide", "small", "teams", "team", "task", "tasks", "project", "projects", "app",
    "apps", "tool", "tools", "software", "free", "pricing", "features", "our", "my", "is", "in",
}  # fmt: skip


# One-word names that are common nouns, never products ("URL", "API", "App").
GENERIC_NAMES = {
    "url", "api", "app", "apps", "cli", "sdk", "ui", "web", "docs", "doc", "tool", "tools",
    "software", "platform", "service", "services", "list", "lists", "link", "links", "code",
    "data", "server", "client", "open", "source", "self", "hosted", "free", "new", "open-source",
}  # fmt: skip


def _compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _aggregators(ws: Path) -> set[str]:
    return {_compact(str(n)) for n in config.resolve("competitors.aggregator_names", ws) if n}


def _is_aggregator_source(src: records.Record, aggregators: set[str]) -> bool:
    host = (urlsplit(src.get("URL").strip()).hostname or "").lower()
    labels = {_compact(label) for label in host.split(".")} | {_compact(host)}
    return bool(labels & aggregators)


def competitor_of(source: records.Record) -> str | None:
    """C ID a source belongs to (``Relevant area: competitor:C-01``), else None."""
    area = source.get("Relevant area").strip()
    if not area.lower().startswith(AREA_PREFIX):
        return None
    return area[len(AREA_PREFIX) :].strip() or None


def _names_in(title: str) -> list[str]:
    out: list[str] = []
    for m in _NAME_RE.finditer(title):
        words = [w for w in m.group(0).split() if w.lower().strip(".,:;") not in _STOP]
        name = " ".join(words).strip(".,:;")
        if name and name not in out:
            out.append(name)
    return out


def candidates(ws: Path) -> dict[str, Any]:
    """Competitor names found in comparison/review source titles (scripts propose, users confirm).

    Names only — no URLs, and never names from model knowledge. The target's own name, our working
    name and competitors already recorded are left out.
    """
    index = WorkspaceIndex(ws)
    st = state.load(ws)
    excluded = {st.product.get("name", ""), st.product.get("our_name", "")}
    excluded |= {c.title for _, c in index.records("C")}
    excluded |= {c.get("Name").strip() for _, c in index.records("C")}
    excluded_norm = {records.normalise_text(n) for n in excluded if n}
    aggregators = _aggregators(ws)
    evidence: dict[str, list[str]] = {}
    comparison_sources: list[str] = []
    for _, src in index.records("S"):
        if competitor_of(src):
            continue
        aggregator = _is_aggregator_source(src, aggregators)
        if aggregator or src.get("Category").strip() in CANDIDATE_CATEGORIES:
            comparison_sources.append(src.id)
        if src.get("Category").strip() not in CANDIDATE_CATEGORIES:
            continue
        for name in _names_in(src.title):
            if records.normalise_text(name) in excluded_norm or _compact(name) in aggregators:
                continue
            if " " not in name and name.lower() in GENERIC_NAMES:
                continue
            evidence.setdefault(name, []).append(src.id)
    ranked = sorted(evidence, key=lambda n: (-len(evidence[n]), n))
    category = ""
    overview = ws / catalog.OVERVIEW_PATH
    if overview.is_file():
        doc = records.parse_document(overview.read_text(encoding="utf-8"))
        category = (doc.section_text("Category") or "").strip()
    cap = int(config.resolve("competitors.max", ws))
    return {
        "candidates": ranked[:cap],
        "evidence": {n: evidence[n] for n in ranked[:cap]},
        "more": ranked[cap:],
        "comparison_sources": sorted(comparison_sources),
        "min_researched": int(config.resolve("competitors.min_researched", ws)),
        "category": category,
        "cap": cap,
        "existing": sorted(c.id for _, c in index.records("C") if records.is_active(c)),
    }


def active_signals(index: WorkspaceIndex) -> list[records.Record]:
    return sorted((r for _, r in index.records("FS") if records.is_active(r)), key=lambda r: r.id)


def competitors_by_feature(index: WorkspaceIndex, signal: str) -> dict[str, set[str]]:
    """F ID → distinct active competitors across active FS signals of one kind."""
    live = {c.id for _, c in index.records("C") if records.is_active(c)}
    out: dict[str, set[str]] = {}
    for fs in active_signals(index):
        if fs.get("Signal").strip() != signal:
            continue
        comps = {c for c in records.parse_refs(fs.get("Competitors")) if c in live}
        for fid in records.parse_refs(fs.get("Feature")):
            out.setdefault(fid, set()).update(comps)
    return out


def offers(index: WorkspaceIndex) -> dict[str, set[str]]:
    """F ID → active competitors that offer it (C ``Table-stakes features`` + table-stakes, rare
    and differentiator signals — a competitor that markets a feature as its edge offers it)."""
    out: dict[str, set[str]] = {}
    for _, c in index.records("C"):
        if records.is_active(c):
            for fid in records.parse_refs(c.get("Table-stakes features")):
                out.setdefault(fid, set()).add(c.id)
    for kind in ("table-stakes", "rare", "differentiator"):
        for fid, comps in competitors_by_feature(index, kind).items():
            out.setdefault(fid, set()).update(comps)
    return out


def table_stakes(index: WorkspaceIndex) -> dict[str, int]:
    """F ID → competitors offering it, for features offered by ≥ TABLE_STAKES_MIN competitors."""
    return {f: len(c) for f, c in sorted(offers(index).items()) if len(c) >= TABLE_STAKES_MIN}


def researched(index: WorkspaceIndex) -> int:
    """Active competitors — "rare" only means something once at least two were researched."""
    return sum(1 for _, c in index.records("C") if records.is_active(c))


def rare(index: WorkspaceIndex) -> list[str]:
    if researched(index) < TABLE_STAKES_MIN:
        return []
    return sorted(f for f, c in offers(index).items() if len(c) == 1)
