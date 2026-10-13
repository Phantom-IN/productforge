"""Counts reported by ``pf.py status`` (IDEA §6 report shape). Scripts count; models don't."""

from __future__ import annotations

from pathlib import Path

from pflib import ids, records
from pflib.index import WorkspaceIndex

CONFIDENCE_STATES = ("CONFIRMED", "PROBABLE", "INFERRED", "UNKNOWN")

# IDEA §6 labels → record prefix
SUMMARY = {
    "sources": "S",
    "claims": "D",
    "unknowns": "U",
    "surfaces": "PS",
    "features": "F",
    "workflows": "W",
    "entities": "E",
    "roles": "RL",
    "permission_rules": "PR",
    "integrations": "I",
    "inferences": "A",
    "competitors": "C",
    "requirements": "R",
    "decisions": "ADR",
    "invariants": "INV",
}


def counts(ws: Path, index: WorkspaceIndex | None = None) -> dict[str, int]:
    """Number of canonical records per prefix (every prefix present, zeros included)."""
    index = index or WorkspaceIndex(ws)
    return {prefix: len(index.records(prefix)) for prefix in ids.PREFIXES}


def confidence_breakdown(ws: Path, index: WorkspaceIndex | None = None) -> dict[str, int]:
    """Confidence of discovery claims (D records)."""
    index = index or WorkspaceIndex(ws)
    out = dict.fromkeys(CONFIDENCE_STATES, 0)
    for _, rec in index.records("D"):
        value = rec.get("Confidence").strip().upper()
        if value in out:
            out[value] += 1
    return out


def active_claims(ws: Path, index: WorkspaceIndex | None = None) -> list[str]:
    """IDs of D records that are neither superseded nor rejected."""
    index = index or WorkspaceIndex(ws)
    return [rec.id for _, rec in index.records("D") if records.is_active(rec)]


def domains(ws: Path, index: WorkspaceIndex | None = None) -> int:
    """Distinct feature domains."""
    index = index or WorkspaceIndex(ws)
    return len(
        {rec.get("Domain").strip() for _, rec in index.records("F") if rec.get("Domain").strip()}
    )


def funnel(ws: Path, index: WorkspaceIndex | None = None) -> dict[str, int | None]:
    """The reduction funnel (IDEA §20): observed → features → requirements → V1 → phases."""
    from pflib import plans, score

    index = index or WorkspaceIndex(ws)
    reqs = [r for _, r in index.records("R") if records.is_active(r)]
    v1 = {r.feature for r in score.evaluate(ws, index) if r.decision in score.IN_V1}
    return {
        "observed_claims": len(active_claims(ws, index)),
        "features": sum(1 for _, f in index.records("F") if records.is_active(f)),
        "core_requirements": sum(1 for r in reqs if r.get("Priority").strip() == "must"),
        "v1_capabilities": len(v1),
        "phases": len(plans.phase_files(ws)) or None,  # None until finalize writes phases
    }


def table_stakes(ws: Path, index: WorkspaceIndex | None = None) -> dict[str, int]:
    """F ID → number of competitors offering it, for table-stakes features (≥ 2 competitors).
    Phase 13 scoring reads it; features without competitor data are absent, i.e. neutral."""
    from pflib import competitors

    return competitors.table_stakes(index or WorkspaceIndex(ws))


def summary(ws: Path, index: WorkspaceIndex | None = None) -> dict[str, int]:
    index = index or WorkspaceIndex(ws)
    per_prefix = counts(ws, index)
    out = {label: per_prefix[prefix] for label, prefix in SUMMARY.items()}
    out["domains"] = domains(ws, index)
    from pflib import domain

    cells = domain.permission_cells(index)
    out["unknown_permission_cells"] = cells["cells"]["?"]
    out["missing_permission_cells"] = cells["missing"]
    return out
