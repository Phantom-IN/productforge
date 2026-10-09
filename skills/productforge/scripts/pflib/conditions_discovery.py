"""DISCOVERY exit-gate conditions (IMPLEMENTATION_PLAN.md §7.2). Registered on import."""

from __future__ import annotations

from pathlib import Path

from pflib import catalog, config, metrics, records, research, taxonomy
from pflib.gates import ConditionResult, GateCondition, register
from pflib.index import WorkspaceIndex

STAGE = "DISCOVERY"
OVERVIEW_REQUIRED = (
    "Product", "One-line description", "Target users", "Category", "Pricing model", "Major areas",
)  # fmt: skip
PLACEHOLDER_PREFIX = "_Not researched yet._"


def _min_sources(ws: Path) -> ConditionResult:
    need = int(config.resolve("research.min_sources_gate", ws))
    have = len(WorkspaceIndex(ws).records("S"))
    return ConditionResult(
        have >= need, f"{have} sources (need ≥ {need}, research.min_sources_gate)"
    )


def _tier1(ws: Path) -> ConditionResult:
    tier1 = [rec.id for _, rec in WorkspaceIndex(ws).records("S") if rec.get("Tier").strip() == "1"]
    if tier1:
        return ConditionResult(True, f"{len(tier1)} Tier 1 sources")
    return ConditionResult(
        False, "no Tier 1 source (official docs, API docs, changelog, security …)"
    )


def coverage_unknowns(ws: Path) -> dict[str, list[str]]:
    """Category → U IDs cited on its line in product-overview.md ``## Coverage``."""
    path = ws / catalog.OVERVIEW_PATH
    if not path.is_file():
        return {}
    body = records.parse_document(path.read_text(encoding="utf-8")).section_text("Coverage") or ""
    out: dict[str, list[str]] = {}
    for line in body.splitlines():
        if line.startswith("- ") and ":" in line:
            category, _, rest = line[2:].partition(":")
            out[category.strip()] = [r for r in records.parse_refs(rest) if r.startswith("U-")]
    return out


def _coverage(ws: Path) -> ConditionResult:
    index = WorkspaceIndex(ws)
    cov = research.coverage(ws, index)
    unknown_ids = set(index.ids("U"))
    explained = {c: [u for u in us if u in unknown_ids] for c, us in coverage_unknowns(ws).items()}
    missing = [c for c in taxonomy.OFFICIAL if not cov[c] and not explained.get(c)]
    if missing:
        return ConditionResult(
            False,
            f"{len(missing)} official categories have neither a source nor an unknown on their "
            f"Coverage line: {', '.join(missing)}",
        )
    by_u = sum(1 for c in taxonomy.OFFICIAL if not cov[c])
    return ConditionResult(True, f"all {len(taxonomy.OFFICIAL)} official categories covered "
                                 f"({by_u} explained by unknowns)")  # fmt: skip


def _overview(ws: Path) -> ConditionResult:
    path = ws / catalog.OVERVIEW_PATH
    if not path.is_file():
        return ConditionResult(False, "product-overview.md is missing")
    doc = records.parse_document(path.read_text(encoding="utf-8"))
    empty = [
        name
        for name in OVERVIEW_REQUIRED
        if not (body := (doc.section_text(name) or "").strip())
        or body.startswith(PLACEHOLDER_PREFIX)
    ]
    if empty:
        return ConditionResult(False, f"overview sections not filled: {', '.join(empty)}")
    return ConditionResult(True, "overview sections filled")


def _surfaces(ws: Path) -> ConditionResult:
    n = len(WorkspaceIndex(ws).records("PS"))
    return ConditionResult(n >= 1, f"{n} product surfaces")


def _min_claims(ws: Path) -> ConditionResult:
    need = int(config.resolve("research.min_claims_gate", ws))
    have = len(metrics.active_claims(ws))
    return ConditionResult(
        have >= need, f"{have} active claims (need ≥ {need}, research.min_claims_gate)"
    )


for _cid, _desc, _fn in (
    ("G-DISC-MIN-SOURCES", "at least research.min_sources_gate sources", _min_sources),
    ("G-DISC-TIER1", "at least one Tier 1 source", _tier1),
    ("G-DISC-COVERAGE", "every official source category has a source or an unknown", _coverage),
    ("G-DISC-OVERVIEW", "product-overview.md sections are filled", _overview),
    ("G-DISC-SURFACES", "at least one product surface", _surfaces),
    ("G-DISC-MIN-CLAIMS", "at least research.min_claims_gate active claims", _min_claims),
):
    register(STAGE, GateCondition(_cid, _desc, _fn))
