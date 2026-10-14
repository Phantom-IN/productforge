"""Traceability (IMPLEMENTATION_PLAN.md §17, IDEA §48–§49): source → claim → feature / workflow /
inference → requirement → decision → phase.

The graph has one node per record ID (and per phase, ``Phase NN``) and an edge ``a → b`` whenever
``a`` cites ``b`` in a reference field (``Evidence``, ``Derived from``, ``Features``, ``Satisfies``,
``Inference``, ``Decision`` …) or a phase cites ``b`` in its ``## References``. "Upstream" follows
citations (towards the evidence); "downstream" follows them backwards (towards the build).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pflib import catalog, ids, plans, records, score
from pflib.index import WorkspaceIndex

PHASE_NODE = "Phase {n}"
EVIDENCE = {"Evidence"}  # what a claim or feature rests on, for the evidence checks
# Structural references (how things relate, where users meet them) are not provenance: a chain
# follows evidence and derivation, not "a task belongs to a workspace".
STRUCTURAL = {
    "Relationships",
    "Inherits",
    "Grants",
    "Resource",
    "Surface",
    "Surfaces",
    "Parent",
    "Table-stakes features",
    "Competitors",
}
# Record types a requirement's chain passes through, by role in the report.
ROLES = {
    "S": "sources",
    "OB": "observations",
    "D": "claims",
    "F": "features",
    "W": "workflows",
    "A": "inferences",
    "E": "entities",
    "I": "integrations",
}


@dataclass
class Graph:
    out: dict[str, list[tuple[str, str]]] = field(default_factory=dict)  # node → [(target, via)]
    into: dict[str, list[tuple[str, str]]] = field(default_factory=dict)  # node → [(source, via)]
    records: dict[str, records.Record] = field(default_factory=dict)
    phases: dict[str, str] = field(default_factory=dict)  # "Phase NN" → rel path

    def add(self, a: str, b: str, via: str) -> None:
        self.out.setdefault(a, []).append((b, via))
        self.into.setdefault(b, []).append((a, via))

    def walk(self, start: str, direction: str, only: set[str] | None = None) -> list[str]:
        """Active records reachable through provenance edges (structural edges are skipped;
        ``only`` restricts the walk to those reference fields)."""
        edges = self.out if direction == "up" else self.into

        def ok(via: str) -> bool:
            return via in only if only is not None else via not in STRUCTURAL

        seen: list[str] = []
        stack = [t for t, via in edges.get(start, []) if ok(via)]
        while stack:
            node = stack.pop()
            if node in seen or node == start or not (node in self.records or node in self.phases):
                continue
            seen.append(node)
            stack.extend(t for t, via in edges.get(node, []) if ok(via))
        return seen


def _active(rec: records.Record) -> bool:
    return records.is_active(rec)


def build(ws: Path, index: WorkspaceIndex | None = None) -> Graph:
    index = index or WorkspaceIndex(ws)
    g = Graph()
    for spec in catalog.CATALOG:
        for rel in index.rel_paths(spec):
            for rec in index.document(rel).records:
                parsed = ids.parse(rec.id, strict=False)
                schema = spec.schema(parsed.prefix) if parsed else None
                if schema is None or not _active(rec):
                    continue
                g.records[rec.id] = rec
                for key in schema.ref_fields:
                    for ref in records.parse_refs(rec.get(key)):
                        g.add(rec.id, ref, key)
    for path in plans.phase_files(ws):
        m = re.match(r"phase-(\d{2})-", path.name)
        if not m:
            continue
        node = PHASE_NODE.format(n=m.group(1))
        g.phases[node] = path.relative_to(ws).as_posix()
        from pflib.phaselint import level2

        refs = level2(path.read_text(encoding="utf-8"))[1].get("References", "")
        for ref in ids.ANY_ID_RE.findall(refs):
            if ids.parse(ref, strict=False) is not None:
                g.add(node, ref, "References")
    return g


def chain(g: Graph, rid: str) -> dict[str, list[str]]:
    """Everything a requirement rests on (by role) and the decisions and phases that build it."""
    up = g.walk(rid, "up")
    out: dict[str, list[str]] = {role: [] for role in ROLES.values()}
    for node in up:
        role = ROLES.get(node.split("-", 1)[0])
        if role:
            out[role].append(node)
    adrs = sorted(a for a, via in g.into.get(rid, []) if a.startswith("ADR-"))
    phases = {a for a, _ in g.into.get(rid, []) if a.startswith("Phase ")}
    for adr in adrs:  # phases that build a decision taken for this requirement
        phases |= {a for a, _ in g.into.get(adr, []) if a.startswith("Phase ")}
    out["adrs"] = adrs
    out["phases"] = sorted(phases)
    return {k: sorted(v) for k, v in out.items()}


@dataclass
class Gap:
    code: str
    rel: str
    record_id: str | None
    message: str


def gaps(ws: Path, g: Graph | None = None, index: WorkspaceIndex | None = None) -> list[Gap]:
    index = index or WorkspaceIndex(ws)
    g = g or build(ws, index)
    out: list[Gap] = []
    locs = {
        rec.id: rel
        for spec in catalog.CATALOG
        for rel in index.rel_paths(spec)
        for rec in index.document(rel).records
    }
    rows = {r.feature: r for r in score.evaluate(ws, index)}
    in_v1 = {f for f, r in rows.items() if r.decision in score.IN_V1}
    planned_ids = {t for node in g.phases for t, _ in g.out.get(node, [])}
    for rid, rec in sorted(g.records.items()):
        prefix = rid.split("-", 1)[0]
        if prefix == "R":
            feats = set(records.parse_refs(rec.get("Features")))
            if feats & in_v1 and rid not in planned_ids:
                out.append(
                    Gap(
                        "TRACE_R_NOT_PLANNED",
                        locs[rid],
                        rid,
                        f"{rid} builds V1 features but no phase cites it",
                    )
                )
            if feats and not feats & in_v1 and rid in planned_ids:
                out.append(
                    Gap(
                        "TRACE_DROPPED_FEATURE_PLANNED",
                        locs[rid],
                        rid,
                        f"{rid} only covers deferred or dropped features but a phase "
                        "plans it (scope leak)",
                    )
                )
        elif prefix == "ADR":
            if rec.get("Status").strip() != "global" and rid not in planned_ids:
                out.append(
                    Gap(
                        "TRACE_ADR_UNUSED",
                        locs[rid],
                        rid,
                        f"{rid} is cited by no phase (mark it `Status: global` if it "
                        "applies everywhere)",
                    )
                )
        elif prefix == "D":
            if not any(n.startswith("S-") for n in g.walk(rid, "up", EVIDENCE)):
                out.append(
                    Gap(
                        "TRACE_D_NO_SOURCE",
                        locs[rid],
                        rid,
                        f"{rid} reaches no source through its evidence",
                    )
                )
        elif prefix == "F":
            up = g.walk(rid, "up", EVIDENCE | {"Derived from"})
            if not any(n.startswith(("S-", "D-")) for n in up):
                out.append(
                    Gap("TRACE_F_NO_EVIDENCE", locs[rid], rid, f"{rid} reaches no claim or source")
                )
    invariants = [rid for rid in g.records if rid.startswith("INV-")]
    docs = " ".join(
        (ws / rel).read_text(encoding="utf-8")
        for rel in (catalog.ROOT_DOCS[2], catalog.PLANS_README_PATH)
        if (ws / rel).is_file()
    )
    for inv in sorted(invariants):
        if inv not in docs and inv not in planned_ids:
            out.append(
                Gap(
                    "TRACE_INV_UNUSED",
                    locs[inv],
                    inv,
                    f"{inv} is in neither CLAUDE.md's golden rules nor the plans index, and "
                    "no phase cites it",
                )
            )
    for node, rel in sorted(g.phases.items()):
        cited = {t.split("-", 1)[0] for t, _ in g.out.get(node, [])}
        if not node.endswith(" 00") and not cited & {"R", "ADR", "INV"}:
            out.append(
                Gap(
                    "TRACE_PHASE_NO_REQUIREMENT",
                    rel,
                    None,
                    f"{node} cites no requirement, decision or invariant",
                )
            )
    return out


def report(ws: Path) -> dict[str, Any]:
    from pflib import validators

    index = WorkspaceIndex(ws)
    g = build(ws, index)
    reqs = sorted(rid for rid in g.records if rid.startswith("R-"))
    chains = {rid: chain(g, rid) for rid in reqs}
    full = [rid for rid, c in chains.items() if c["sources"] and c["phases"]]
    found = [validators.finding(x.code, x.rel, x.record_id, x.message) for x in gaps(ws, g, index)]
    return {
        "requirements": len(reqs),
        "fully_traced": len(full),
        "errors": sum(f.severity == validators.ERROR for f in found),
        "warnings": sum(f.severity == validators.WARN for f in found),
        "findings": [f.to_dict() for f in found],
        "chains": chains,
    }


def explain(ws: Path, node: str) -> dict[str, Any]:
    g = build(ws)
    if node not in g.records and node not in g.phases:
        from pflib.errors import UsageError

        raise UsageError(f"{node} is not an active record or phase", code="UNKNOWN_ID")

    def tree(
        start: str, direction: str, depth: int = 0, seen: set[str] | None = None
    ) -> list[dict[str, Any]]:
        seen = seen if seen is not None else {start}
        edges = g.out if direction == "up" else g.into
        out = []
        for target, via in sorted(set(edges.get(start, []))):
            if target in seen or depth > 6 or via in STRUCTURAL:
                continue
            seen.add(target)
            out.append(
                {"id": target, "via": via, "children": tree(target, direction, depth + 1, seen)}
            )
        return out

    return {"id": node, "upstream": tree(node, "up"), "downstream": tree(node, "down")}


def describe(node: str, g_records: dict[str, records.Record]) -> str:
    rec = g_records.get(node)
    if rec is None:
        return node
    if node.startswith("S-"):
        return f"{node} (Tier {rec.get('Tier').strip()}) {rec.get('URL').strip()}"
    return f"{node} {rec.title}"
