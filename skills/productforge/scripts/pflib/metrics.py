"""Counts reported by ``pf.py status`` (IDEA §6 report shape). Scripts count; models don't."""

from __future__ import annotations

from pathlib import Path

from pflib import ids
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


INACTIVE_STATUS_PREFIXES = ("superseded-by", "rejected")


def active_claims(ws: Path, index: WorkspaceIndex | None = None) -> list[str]:
    """IDs of D records that are neither superseded nor rejected."""
    index = index or WorkspaceIndex(ws)
    return [
        rec.id
        for _, rec in index.records("D")
        if not rec.get("Status").strip().startswith(INACTIVE_STATUS_PREFIXES)
    ]


def domains(ws: Path, index: WorkspaceIndex | None = None) -> int:
    """Distinct feature domains."""
    index = index or WorkspaceIndex(ws)
    return len(
        {rec.get("Domain").strip() for _, rec in index.records("F") if rec.get("Domain").strip()}
    )


def summary(ws: Path, index: WorkspaceIndex | None = None) -> dict[str, int]:
    index = index or WorkspaceIndex(ws)
    per_prefix = counts(ws, index)
    out = {label: per_prefix[prefix] for label, prefix in SUMMARY.items()}
    out["domains"] = domains(ws, index)
    return out
