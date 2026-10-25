"""PHASE_PLAN_READY exit-gate conditions built in Phase 15 (root documents, phase lint)."""

from __future__ import annotations

from pathlib import Path

from pflib import catalog, plans, validators
from pflib.gates import ConditionResult, GateCondition, register

STAGE = "PHASE_PLAN_READY"


def _root_docs(ws: Path) -> ConditionResult:
    issues = plans.root_doc_issues(ws)
    if not issues and not (ws / catalog.IMPLEMENTATION_PLAN_PATH).is_file():
        return ConditionResult(False, "no root documents yet (/productforge finalize)")
    if issues:
        return ConditionResult(False, "; ".join(f"{i.rel}: {i.message}" for i in issues[:4]))
    return ConditionResult(
        True,
        "README, IMPLEMENTATION_PLAN, CLAUDE, DEVELOPMENT, STARTUP_PROMPT, "
        "ORCHESTRATOR_PROMPT complete",
    )


def _phase_lint(ws: Path) -> ConditionResult:
    res = plans.lint(ws)
    if not res.phases:
        return ConditionResult(False, "no phase files yet (/productforge finalize)")
    # Heuristic cross-phase warnings are advisory; only error-level findings block the gate.
    errors = [
        i
        for i in res.issues
        if validators.CODES.get(i.code, (validators.ERROR,))[0] != validators.WARN
    ]
    warnings = len(res.issues) - len(errors)
    if errors:
        codes = sorted({i.code for i in errors})
        return ConditionResult(
            False, f"{len(errors)} lint error(s): {', '.join(codes)} (pf.py lint-phases)"
        )
    tail = f"; {warnings} warning(s) to review" if warnings else ""
    return ConditionResult(True, f"{len(res.phases)} phases, no lint errors{tail}")


def _trace_clean(ws: Path) -> ConditionResult:
    from pflib import trace

    if not plans.phase_files(ws):
        return ConditionResult(False, "no phase files yet (/productforge finalize)")
    rep = trace.report(ws)
    if rep["errors"]:
        codes = sorted({f["code"] for f in rep["findings"] if f["severity"] == "error"})
        return ConditionResult(
            False, f"{rep['errors']} trace error(s): {', '.join(codes)} (pf.py trace)"
        )
    return ConditionResult(
        True,
        f"{rep['fully_traced']}/{rep['requirements']} requirements traced from a source to a phase",
    )


def _traceability_rendered(ws: Path) -> ConditionResult:
    from pflib import render
    from pflib.index import WorkspaceIndex

    path = ws / catalog.TRACEABILITY_PATH
    if not path.is_file():
        return ConditionResult(False, f"{catalog.TRACEABILITY_PATH} missing (pf.py trace --write)")
    text = path.read_text(encoding="utf-8")
    if render.render_text(catalog.TRACEABILITY_PATH, text, WorkspaceIndex(ws)) != text:
        return ConditionResult(False, f"{catalog.TRACEABILITY_PATH} is stale (pf.py trace --write)")
    return ConditionResult(True, f"{catalog.TRACEABILITY_PATH} matches a fresh render")


register(STAGE, GateCondition("G-PP-TRACE-CLEAN", "pf.py trace reports no errors", _trace_clean))
register(
    STAGE,
    GateCondition(
        "G-PP-TRACEABILITY-RENDERED",
        "TRACEABILITY.md matches a fresh render",
        _traceability_rendered,
    ),
)
register(
    STAGE,
    GateCondition("G-PP-ROOT-DOCS", "root documents exist with required sections", _root_docs),
)
register(STAGE, GateCondition("G-PP-PHASE-LINT", "pf.py lint-phases reports no error", _phase_lint))
