"""Generated views over records (IMPLEMENTATION_PLAN.md §6.2: records canonical, tables views).

A generated region looks like::

    <!-- pf:generated:start matrix -->
    | ID | Domain | … |
    <!-- pf:generated:end -->

Renderers rebuild a region's body from canonical records; everything outside the markers is
left untouched. ``merge`` re-renders after every write, so regions are never stale in normal
use; ``pf.py validate`` flags a region that differs from a fresh render
(``GENERATED_REGION_EDITED``). Lock snapshots only hash records, so views never trip locks.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pflib import catalog, records
from pflib.index import WorkspaceIndex
from pflib.io import atomic_write_text

START = "<!-- pf:generated:start {name} -->"
END = "<!-- pf:generated:end -->"
REGION_RE = re.compile(
    r"<!-- pf:generated:start (?P<name>[\w-]+) -->\n(?P<body>.*?)<!-- pf:generated:end -->", re.S
)

FEATURE_MATRIX = catalog.FEATURE_MATRIX_PATH
SURFACES = catalog.SURFACES_PATH
MATRIX_COLUMNS = ("ID", "Domain", "Feature", "Parent", "Surface", "Evidence", "Confidence",
                  "Plan tier", "Complexity", "MVP", "Decision", "Score")  # fmt: skip


@dataclass(frozen=True)
class Renderer:
    regions: Callable[[WorkspaceIndex], dict[str, str]]  # region name → body ("" = skip)
    headings: dict[str, str]  # region name → "## Heading" to create when the region is missing


def _cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", "\\|").strip() or "—"


def _num(value: float) -> str:
    return str(int(value)) if value == int(value) else f"{value:.1f}"


def _features(index: WorkspaceIndex) -> list[records.Record]:
    return [rec for _, rec in index.records("F") if records.is_active(rec)]


def feature_regions(index: WorkspaceIndex) -> dict[str, str]:
    feats = _features(index)
    if not feats:
        return {"hierarchy": "_No features yet._\n", "matrix": "_No features yet._\n"}
    by_id = {f.id: f for f in feats}
    children: dict[str, list[records.Record]] = {}
    roots: dict[str, list[records.Record]] = {}
    for f in feats:
        parent = next(iter(records.parse_refs(f.get("Parent"))), "")
        if parent in by_id:
            children.setdefault(parent, []).append(f)
        else:
            roots.setdefault(f.get("Domain").strip() or "(no domain)", []).append(f)
    lines: list[str] = []
    seen: set[str] = set()

    def walk(rec: records.Record, depth: int) -> None:
        if rec.id in seen:  # cycles are reported by the validator; never loop here
            return
        seen.add(rec.id)
        lines.append(f"{'  ' * depth}- {rec.id} {rec.get('Feature').strip() or rec.title}")
        for child in sorted(children.get(rec.id, []), key=lambda r: r.id):
            walk(child, depth + 1)

    for domain in sorted(roots):
        lines.append(f"- **{domain}**")
        for rec in sorted(roots[domain], key=lambda r: r.id):
            walk(rec, 1)
    from pflib import score

    scored = {r.feature: r for r in score.evaluate(index.ws, index)}  # empty before scoping
    header = "| " + " | ".join(MATRIX_COLUMNS) + " |"
    rows = [header, "|" + "|".join("---" for _ in MATRIX_COLUMNS) + "|"]
    for f in sorted(feats, key=lambda r: (r.get("Domain").strip(), r.id)):
        row = scored.get(f.id)
        scope_cells = ["", "", ""]
        if row is not None and row.decision:
            mvp = "yes" if row.decision in score.IN_V1 else "no"
            prio = "" if row.priority is None else _num(row.priority)
            scope_cells = [mvp, row.decision + (" (override)" if row.override else ""), prio]
        values = [f.id] + [f.get(col) for col in MATRIX_COLUMNS[1:9]] + scope_cells
        rows.append("| " + " | ".join(_cell(v) for v in values) + " |")
    return {"hierarchy": "\n".join(lines) + "\n", "matrix": "\n".join(rows) + "\n"}


def surface_regions(index: WorkspaceIndex) -> dict[str, str]:
    feats = _features(index)
    if not feats:
        return {"surface-features": ""}  # nothing to show before PRODUCT_MODEL
    rows = ["| Surface | Features |", "|---|---|"]
    for _, ps in index.records("PS"):
        linked = sorted(f.id for f in feats if ps.id in records.parse_refs(f.get("Surface")))
        rows.append(f"| {ps.id} {_cell(ps.title)} | {', '.join(linked) or '—'} |")
    return {"surface-features": "\n".join(rows) + "\n"}


def workflow_regions(index: WorkspaceIndex) -> dict[str, str]:
    from pflib import workflows

    flows = [(rel, w) for rel, w in index.records("W") if records.is_active(w)]
    if not flows:
        return {"workflows": ""}
    rows = ["| W | Name | Actor | Features | Confidence | Implied system steps |",
            "|---|---|---|---|---|---|"]  # fmt: skip
    for rel, w in sorted(flows, key=lambda x: x[1].id):
        steps, _ = workflows.parse_steps(index.document(rel).text)
        implied = sum(1 for s in steps if s.tag == "implied-system")
        cells = [
            w.id,
            w.title,
            w.get("Actor"),
            w.get("Features"),
            w.get("Confidence"),
            str(implied),
        ]
        rows.append("| " + " | ".join(_cell(c) for c in cells) + " |")
    return {"workflows": "\n".join(rows) + "\n"}


def domain_regions(index: WorkspaceIndex) -> dict[str, str]:
    from pflib import domain

    ents = domain.active(index, "E")
    if not ents:
        return {"relationship-tree": "_No entities yet._\n", "identity": "_No entities yet._\n"}
    rows = ["| Entity | Identity scheme | Human-readable key | Stable after creation? | Evidence |",
            "|---|---|---|---|---|"]  # fmt: skip
    for e in ents:
        cells = [f"{e.id} {e.title}", e.get("Identity"), e.get("Human-readable key"),
                 e.get("Stable after creation"), e.get("Evidence")]  # fmt: skip
        rows.append("| " + " | ".join(_cell(c) for c in cells) + " |")
    return {
        "relationship-tree": "\n".join(domain.relationship_tree(index)) + "\n",
        "identity": "\n".join(rows) + "\n",
    }


def permission_regions(index: WorkspaceIndex) -> dict[str, str]:
    from pflib import domain

    roles, rules = domain.matrix_rows(index)
    if not rules:
        return {"permissions": "_No permission rules yet._\n"}
    entities = {e.id: e for e in domain.active(index, "E")}
    header = ["Resource", "Action", *(f"{r.id} {r.title}" for r in roles), "Rule"]
    rows = ["| " + " | ".join(_cell(h) for h in header) + " |",
            "|" + "|".join("---" for _ in header) + "|"]  # fmt: skip
    for rule in rules:
        cells, _ = domain.parse_grants(rule.get("Grants"))
        res = next(iter(records.parse_refs(rule.get("Resource"))), "")
        label = f"{res} {entities[res].title}" if res in entities else rule.get("Resource")
        values = [label, rule.get("Action"), *(cells.get(r.id, "") for r in roles), rule.id]
        rows.append("| " + " | ".join(_cell(v) for v in values) + " |")
    return {"permissions": "\n".join(rows) + "\n"}


def integration_regions(index: WorkspaceIndex) -> dict[str, str]:
    from pflib import domain

    integrations = domain.active(index, "I")
    if not integrations:
        return {"integrations": "_No integrations yet._\n"}
    rows = [
        "| I | Provider | Direction | Auth | Events | Confidence |",
        "|---|---|---|---|---|---|",
    ]
    for i in integrations:
        cells = [i.id, i.title, i.get("Direction"), i.get("Authentication"), i.get("Events"),
                 i.get("Confidence")]  # fmt: skip
        rows.append("| " + " | ".join(_cell(c) for c in cells) + " |")
    return {"integrations": "\n".join(rows) + "\n"}


def inference_regions(index: WorkspaceIndex) -> dict[str, str]:
    from pflib import domain, workflows

    inferences = domain.active(index, "A")
    if not inferences:
        return {"areas": "_No inferences yet._\n", "workflow-coverage": "_No inferences yet._\n"}
    by_area: dict[str, list[records.Record]] = {}
    for a in inferences:
        by_area.setdefault(a.get("Area").strip() or "(no area)", []).append(a)
    areas = []
    for area in sorted(by_area):
        areas.append(f"- **{area}**")
        areas.extend(f"  - {a.id} {_cell(a.title)}" for a in by_area[area])
    rows = ["| W | Workflow | Implied system steps | Requirements surfaced | A refs |",
            "|---|---|---|---|---|"]  # fmt: skip
    for rel, w in sorted(index.records("W"), key=lambda x: x[1].id):
        if not records.is_active(w):
            continue
        text = index.document(rel).text
        steps, _ = workflows.parse_steps(text)
        implied = sum(1 for s in steps if s.tag == "implied-system")
        surfaced = workflows.requirements_surfaced(text)
        refs = [a.id for a in inferences if w.id in records.parse_refs(a.get("Derived from"))]
        cells = [w.id, w.title, str(implied), str(len(surfaced)), ", ".join(refs)]
        rows.append("| " + " | ".join(_cell(c) for c in cells) + " |")
    return {"areas": "\n".join(areas) + "\n", "workflow-coverage": "\n".join(rows) + "\n"}


def competitor_regions(index: WorkspaceIndex) -> dict[str, str]:
    from pflib import competitors, domain

    comps = domain.active(index, "C")
    signals = competitors.active_signals(index)
    if not comps:
        return {"landscape": "_No competitors yet._\n", "signals": "_No feature signals yet._\n",
                "absent": "_None recorded._\n"}  # fmt: skip
    offered = competitors.offers(index)
    stakes = {f: offered[f] for f in competitors.table_stakes(index)}
    rows = ["| C | Name | Positioning | Pricing | Table-stakes overlaps |", "|---|---|---|---|---|"]
    for c in comps:
        overlaps = sum(1 for members in stakes.values() if c.id in members)
        cells = [c.id, c.get("Name") or c.title, c.get("Positioning"), c.get("Pricing model"),
                 str(overlaps)]  # fmt: skip
        rows.append("| " + " | ".join(_cell(x) for x in cells) + " |")
    diffs = competitors.competitors_by_feature(index, "differentiator")
    features = {f.id: f for f in domain.active(index, "F")}
    sig_rows = ["| F | Feature | Offered by | Table stakes | Differentiator |",
                "|---|---|---|---|---|"]  # fmt: skip
    for fid in sorted(set(offered) | set(diffs)):
        f = features.get(fid)
        name = (f.get("Feature").strip() or f.title) if f else "—"
        n = len(offered.get(fid, ()))
        if len(comps) < competitors.TABLE_STAKES_MIN:
            verdict = "— (1 competitor)"  # table stakes and rarity need ≥ 2 researched
        else:
            verdict = "yes" if fid in stakes else ("rare" if n == 1 else "no")
        counts = [n, verdict, len(diffs.get(fid, ()))]
        sig_rows.append("| " + " | ".join(_cell(x) for x in [fid, name, *map(str, counts)]) + " |")
    absent = [s for s in signals if s.get("Signal").strip() == competitors.ABSENT]
    absent_rows = ["| Capability | Competitors | Signal |", "|---|---|---|"]
    for s in absent:
        absent_rows.append(
            f"| {_cell(s.get('Feature'))} | {_cell(s.get('Competitors'))} | {s.id} |"
        )
    return {
        "landscape": "\n".join(rows) + "\n",
        "signals": ("\n".join(sig_rows) if len(sig_rows) > 2 else "_No feature signals yet._")
        + "\n",
        "absent": ("\n".join(absent_rows) if absent else "_None recorded._") + "\n",
    }


OUR_V1 = {"BUILD NOW": "✓", "BUILD SIMPLIFIED": "Simplified", "USE EXTERNAL SERVICE": "External",
          "DEFER": "✗", "DROP": "✗"}  # fmt: skip


def parity_regions(index: WorkspaceIndex) -> dict[str, str]:
    from pflib import domain, score

    rows = score.evaluate(index.ws, index)
    if not rows:
        return {"parity": "_No score cards yet._\n", "overrides": "_No overrides._\n"}
    feats = {f.id: f for f in domain.active(index, "F")}
    cards = {sc.id: sc for _, sc in index.records("SC")}
    out = ["| Feature | Target | Our V1 | Future | Decision | Notes |", "|---|---|---|---|---|---|"]
    overrides = []
    for r in rows:
        f, sc = feats.get(r.feature), cards[r.sc]
        name = f"{r.feature} {(f.get('Feature').strip() or f.title) if f else '?'}"
        conf = f.get("Confidence").strip() if f else ""
        target = "✓" if conf in ("", "CONFIRMED") else f"✓ ({conf})"
        notes = [sc.get("Simplification"), sc.get("External service")]
        if r.table_stakes:
            notes.append(f"table stakes ({r.table_stakes} competitors)")
        if r.priority is None:
            notes.append(r.rule)
        decision = (r.decision or "—") + (" (override)" if r.override else "")
        cells = [name, target, OUR_V1.get(r.decision or "", "—"), sc.get("Future"), decision,
                 "; ".join(n.strip() for n in notes if n and n.strip())]  # fmt: skip
        out.append("| " + " | ".join(_cell(c) for c in cells) + " |")
        if r.override:
            overrides.append(f"- {r.sc} {r.feature}: computed {r.computed or '—'} → {r.override} — "
                             f"{_cell(sc.get('Override reason'))}")  # fmt: skip
    return {
        "parity": "\n".join(out) + "\n",
        "overrides": ("\n".join(overrides) if overrides else "_No overrides._") + "\n",
    }


def product_spec_regions(index: WorkspaceIndex) -> dict[str, str]:
    from pflib import metrics

    f = metrics.funnel(index.ws, index)
    labels = (
        ("observed_claims", "Observed claims"),
        ("features", "Features reconstructed"),
        ("core_requirements", "Core requirements (must)"),
        ("v1_capabilities", "V1 capabilities (built or external)"),
        ("phases", "Phases"),
    )
    funnel = ["| Step | Count |", "|---|---:|"]
    funnel += [f"| {label} | {'—' if f[key] is None else f[key]} |" for key, label in labels]
    uds = [ud for _, ud in index.records("UD") if records.is_active(ud)]
    questions = {u.id: u for _, u in index.records("U")}
    if uds:
        defaults = ["| Unknown | Question | V1 default | Impact if wrong |", "|---|---|---|---|"]
        for ud in sorted(uds, key=lambda r: r.id):
            uid = next(iter(records.parse_refs(ud.get("Unknown"))), "")
            q = questions.get(uid)
            cells = [uid, q.get("Question") if q else "—", ud.get("V1 default"),
                     ud.get("Impact if wrong")]  # fmt: skip
            defaults.append("| " + " | ".join(_cell(c) for c in cells) + " |")
        accepted = "\n".join(defaults) + "\n"
    else:
        accepted = "_No defaults accepted yet._\n"
    return {"funnel": "\n".join(funnel) + "\n", "defaults": accepted}


RENDERERS: dict[str, Renderer] = {
    FEATURE_MATRIX: Renderer(feature_regions, {"hierarchy": "## Hierarchy", "matrix": "## Matrix"}),
    SURFACES: Renderer(surface_regions, {"surface-features": "## Surface → features"}),
    catalog.RESEARCH_README_PATH: Renderer(workflow_regions, {"workflows": "## Workflows"}),
    catalog.DOMAIN_MODEL_PATH: Renderer(
        domain_regions,
        {"relationship-tree": "## Relationship tree", "identity": "## Identity decisions"},
    ),
    catalog.PERMISSIONS_PATH: Renderer(permission_regions, {"permissions": "## Matrix"}),
    catalog.INTEGRATIONS_PATH: Renderer(integration_regions, {"integrations": "## Summary"}),
    catalog.PARITY_PATH: Renderer(
        parity_regions, {"parity": "## Matrix", "overrides": "## Overrides"}
    ),
    catalog.PRODUCT_SPEC_PATH: Renderer(
        product_spec_regions, {"funnel": "## Reduction funnel", "defaults": "## Accepted defaults"}
    ),
    catalog.COMPETITORS_PATH: Renderer(
        competitor_regions,
        {
            "landscape": "## Landscape",
            "signals": "## Signals by feature",
            "absent": "## Missing in target",
        },
    ),
    catalog.INFERENCE_PATH: Renderer(
        inference_regions,
        {"areas": "## Requirement areas", "workflow-coverage": "## Workflow coverage"},
    ),
}
assert all(catalog.spec_for_path(rel) is not None for rel in RENDERERS)


def regions(text: str) -> dict[str, str]:
    return {m.group("name"): m.group("body") for m in REGION_RE.finditer(text)}


def apply(text: str, bodies: dict[str, str], headings: dict[str, str]) -> str:
    """Replace each named region's body; create missing regions under their heading at the end."""
    present = regions(text)

    def replace(m: re.Match[str]) -> str:
        name = m.group("name")
        if name not in bodies or not bodies[name]:
            return m.group(0)
        return f"{START.format(name=name)}\n{bodies[name]}{END}"

    out = REGION_RE.sub(replace, text)
    for name, body in bodies.items():
        if name in present or not body:
            continue
        if not out.endswith("\n"):
            out += "\n"
        if not out.endswith("\n\n"):
            out += "\n"
        out += f"{headings[name]}\n\n{START.format(name=name)}\n{body}{END}\n"
    return out


def render_text(rel: str, text: str, index: WorkspaceIndex) -> str:
    renderer = RENDERERS.get(rel)
    if renderer is None:
        return text
    return apply(text, renderer.regions(index), renderer.headings)


def render_all(ws: Path, only: str | None = None) -> list[str]:
    """Re-render every renderer-backed artifact that exists; returns the files that changed."""
    index = WorkspaceIndex(ws)
    changed: list[str] = []
    for rel in sorted(RENDERERS):
        if only is not None and rel != only:
            continue
        path = ws / rel
        if not path.is_file():
            continue
        old = path.read_text(encoding="utf-8")
        new = render_text(rel, old, index)
        if new != old:
            atomic_write_text(path, new)
            changed.append(rel)
    return changed
