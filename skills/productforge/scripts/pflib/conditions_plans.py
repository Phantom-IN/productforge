"""PHASE_PLAN_READY exit-gate conditions built in Phase 15 (root documents, phase lint)."""

from __future__ import annotations

from pathlib import Path

from pflib import catalog, plans
from pflib.gates import ConditionResult, GateCondition, register

STAGE = "PHASE_PLAN_READY"


def _root_docs(ws: Path) -> ConditionResult:
    issues = plans.root_doc_issues(ws)
    if not issues and not (ws / catalog.IMPLEMENTATION_PLAN_PATH).is_file():
        return ConditionResult(False, "no root documents yet (/productforge finalize)")
    if issues:
        return ConditionResult(False, "; ".join(f"{i.rel}: {i.message}" for i in issues[:4]))
    return ConditionResult(
        True, "README, IMPLEMENTATION_PLAN, CLAUDE, DEVELOPMENT, STARTUP_PROMPT complete"
    )


def _phase_lint(ws: Path) -> ConditionResult:
    res = plans.lint(ws)
    if not res.phases:
        return ConditionResult(False, "no phase files yet (/productforge finalize)")
    if res.issues:
        codes = sorted({i.code for i in res.issues})
        return ConditionResult(False, f"{len(res.issues)} lint finding(s): {', '.join(codes)} "
                                      "(pf.py lint-phases)")  # fmt: skip
    return ConditionResult(True, f"{len(res.phases)} phases, pf.py lint-phases clean")


register(STAGE, GateCondition("G-PP-ROOT-DOCS", "root documents exist with required sections",
                              _root_docs))  # fmt: skip
register(STAGE, GateCondition("G-PP-PHASE-LINT", "pf.py lint-phases is clean", _phase_lint))
