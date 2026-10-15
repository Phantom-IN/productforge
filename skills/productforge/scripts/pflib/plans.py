"""Generated project plans in a workspace: lint input and status.

Builds a ``phaselint.PlanSet`` from the workspace — phase files, the plans index, the
implementation plan, the repository tree declared in ``spec/ARCHITECTURE.md`` and the record IDs
that exist — so validators, gates, ``pf.py lint-phases`` and ``status`` share one view.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pflib import architecture, catalog, config, phaselint, records
from pflib.index import WorkspaceIndex


def _read(ws: Path, rel: str) -> str | None:
    path = ws / rel
    return path.read_text(encoding="utf-8") if path.is_file() else None


def phase_files(ws: Path) -> list[Path]:
    return sorted(p for p in ws.glob(catalog.PHASES_GLOB) if p.is_file())


def plan_set(ws: Path, index: WorkspaceIndex | None = None) -> phaselint.PlanSet:
    index = index or WorkspaceIndex(ws)
    arch = architecture.text_of(ws)
    tree = architecture.tree(arch)[0] if arch else None
    known = {rec.id for spec in catalog.CATALOG for rel in index.rel_paths(spec)
             for rec in index.document(rel).records}  # fmt: skip
    return phaselint.PlanSet(
        phases={
            p.relative_to(ws).as_posix(): p.read_text(encoding="utf-8") for p in phase_files(ws)
        },
        plan_text=_read(ws, catalog.IMPLEMENTATION_PLAN_PATH),
        plan_rel=catalog.IMPLEMENTATION_PLAN_PATH,
        readme_text=_read(ws, catalog.PLANS_README_PATH),
        readme_rel=catalog.PLANS_README_PATH,
        tree=tree or None,
        known_ids=known,
        breakdown_section=19,
        max_tasks=int(config.resolve("phases.max_tasks", ws)),
        min_acceptance=int(config.resolve("phases.min_acceptance", ws)),
        extra_roots=catalog.WORKSPACE_ROOTS,
    )


def lint(ws: Path) -> phaselint.Result:
    """Phase lint, or an empty result before any phase file exists."""
    if not phase_files(ws):
        return phaselint.Result()
    return phaselint.lint(plan_set(ws))


def root_doc_issues(ws: Path) -> list[phaselint.Issue]:
    """Root-document checks, once finalize has written any root document."""
    texts = {rel: _read(ws, rel) for rel in catalog.ROOT_DOCS}
    if all(v is None for v in texts.values()):
        return []
    invariants = sum(1 for _, r in WorkspaceIndex(ws).records("INV") if records.is_active(r))
    return phaselint.lint_root_docs(texts, invariants)


def implementation_detected(ws: Path, gate_passed: bool) -> bool:
    """Work has begun when the plan is ready and any phase left `Not started`."""
    readme = _read(ws, catalog.PLANS_README_PATH)
    if not gate_passed or readme is None:
        return False
    statuses = re.findall(r"^\|\s*\d{2}\s*\|[^|]*\|[^|]*\|\s*([^|]+?)\s*\|", readme, re.M)
    return any(s.lower() != "not started" for s in statuses)


def report(ws: Path) -> dict[str, Any]:
    from pflib import validators

    res = lint(ws)
    issues = res.issues + root_doc_issues(ws)
    found = [validators.finding(i.code, i.rel, None, i.message) for i in issues]
    return {
        "errors": sum(f.severity == validators.ERROR for f in found),
        "warnings": sum(f.severity == validators.WARN for f in found),
        "findings": [f.to_dict() for f in found],
        "phases": res.summary(),
    }
