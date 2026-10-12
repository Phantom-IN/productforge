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
    header = "| " + " | ".join(MATRIX_COLUMNS) + " |"
    rows = [header, "|" + "|".join("---" for _ in MATRIX_COLUMNS) + "|"]
    for f in sorted(feats, key=lambda r: (r.get("Domain").strip(), r.id)):
        values = [f.id] + [f.get(col) for col in MATRIX_COLUMNS[1:9]] + ["", "", ""]
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


RENDERERS: dict[str, Renderer] = {
    FEATURE_MATRIX: Renderer(feature_regions, {"hierarchy": "## Hierarchy", "matrix": "## Matrix"}),
    SURFACES: Renderer(surface_regions, {"surface-features": "## Surface → features"}),
    catalog.RESEARCH_README_PATH: Renderer(workflow_regions, {"workflows": "## Workflows"}),
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
