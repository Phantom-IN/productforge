"""Feature planning — ``pf.py feature-plan``. Scripts count."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pflib import catalog, config, records
from pflib.index import WorkspaceIndex

SOFT_CAP = 120  # beyond this, minor capabilities should become sub-features


def domains(ws: Path) -> list[dict[str, str]]:
    """Domains from ``## Domains`` in FEATURE_MATRIX.md: ``- <Domain>: <description>`` lines."""
    path = ws / catalog.FEATURE_MATRIX_PATH
    if not path.is_file():
        return []
    body = records.parse_document(path.read_text(encoding="utf-8")).section_text("Domains") or ""
    out = []
    for line in body.splitlines():
        if line.startswith("- ") and ":" in line:
            name, _, desc = line[2:].partition(":")
            if name.strip():
                out.append({"name": name.strip().strip("*"), "description": desc.strip()})
    return out


def plan(ws: Path) -> dict[str, Any]:
    index = WorkspaceIndex(ws)
    feats = [rec for _, rec in index.records("F") if records.is_active(rec)]
    names = [d["name"] for d in domains(ws)]
    per_domain = {name: 0 for name in names}
    unlisted: dict[str, int] = {}
    for f in feats:
        dom = f.get("Domain").strip()
        if dom in per_domain:
            per_domain[dom] += 1
        else:
            unlisted[dom] = unlisted.get(dom, 0) + 1
    surfaces = [rec for _, rec in index.records("PS")]
    covered = {ref for f in feats for ref in records.parse_refs(f.get("Surface"))}
    return {
        "domains": domains(ws),
        "features": len(feats),
        "features_per_domain": per_domain,
        "features_in_unlisted_domains": unlisted,
        "empty_domains": [n for n, c in per_domain.items() if c == 0],
        "surfaces": len(surfaces),
        "surfaces_without_features": [ps.id for ps in surfaces if ps.id not in covered],
        "max_parallel": int(config.resolve("features.max_parallel_domains", ws)),
        "soft_cap": SOFT_CAP,
        # each domain pass only sees its own domain, so the overall cap is split across domains
        "per_domain_budget": max(5, -(-SOFT_CAP // max(1, len(names)))),
        "over_soft_cap": len(feats) > SOFT_CAP,
    }
