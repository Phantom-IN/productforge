"""Stage exit gates (IMPLEMENTATION_PLAN.md §7.2).

``EXPECTED`` declares, per stage, every condition the gate is made of and the phase that
implements it. ``REGISTRY`` holds the implemented checks. A declared condition with no
implementation reports ``not built`` and fails, so no stage can be advanced on checks
that do not exist yet. Phases register their checks with ``register(stage, condition)``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pflib import workspace
from pflib.errors import PFError

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_NOT_BUILT = "not_built"
STATUS_ERROR = "error"


@dataclass
class ConditionResult:
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class GateCondition:
    id: str
    description: str
    check: Callable[[Path], ConditionResult]


@dataclass
class ResultRow:
    id: str
    passed: bool
    status: str
    description: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "passed": self.passed,
            "status": self.status,
            "description": self.description,
            "detail": self.detail,
        }


@dataclass
class GateReport:
    stage: str
    results: list[ResultRow] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.results) and all(r.passed for r in self.results)

    @property
    def progress(self) -> tuple[int, int]:
        return sum(r.passed for r in self.results), len(self.results)

    def failing(self) -> list[str]:
        return [r.id for r in self.results if not r.passed]

    def to_dict(self) -> dict[str, Any]:
        done, total = self.progress
        return {
            "stage": self.stage,
            "passed": self.passed,
            "progress": f"{done}/{total}",
            "results": [r.to_dict() for r in self.results],
        }


# ------------------------------------------------------------------- declared gates

_GENERIC = [
    ("G-STATE-FILE-VALID", "state.json is present and valid", "02"),
    ("G-NO-UNMERGED-STAGING", "no staging run is waiting to be merged", "02"),
    ("G-VALIDATE-CLEAN", "pf.py validate reports no errors for this stage", "03"),
]

# stage → [(condition id, description, implementing phase)]
EXPECTED: dict[str, list[tuple[str, str, str]]] = {
    "DISCOVERY": _GENERIC
    + [
        ("G-SCOPE-SET", "a scope is set and accepted", "02"),
        ("G-DISC-MIN-SOURCES", "at least research.min_sources_gate sources", "07"),
        ("G-DISC-TIER1", "at least one Tier 1 source", "07"),
        ("G-DISC-COVERAGE", "every official source category has a source or an unknown", "07"),
        ("G-DISC-OVERVIEW", "product-overview.md sections are filled", "07"),
        ("G-DISC-SURFACES", "at least one product surface", "07"),
        ("G-DISC-MIN-CLAIMS", "at least research.min_claims_gate active claims", "07"),
    ],
    "PRODUCT_MODEL": _GENERIC
    + [
        ("G-PM-SURFACE-FEATURES", "every product surface maps to a feature", "11"),
        ("G-PM-FEATURE-EVIDENCE", "every feature cites evidence or is derived", "11"),
        ("G-PM-WORKFLOW-PER-DOMAIN", "every core domain has a workflow", "11"),
        ("G-PM-ENTITY-COMPLETE", "entities have identity, lifecycle, deletion semantics", "11"),
        ("G-PM-PERMISSIONS-COVERAGE", "mutable entities have permission rules", "11"),
        ("G-PM-INTEGRATIONS-COMPLETE", "integrations have direction and authentication", "11"),
        ("G-PM-INFERENCE-COMPLETE", "architecture inferences are complete", "11"),
    ],
    "SCOPE_DEFINED": _GENERIC
    + [
        ("G-SC-ALL-SCORED", "every feature has a score card", "13"),
        ("G-SC-DECISIONS-COMPUTED", "decisions match a fresh pf.py score run", "13"),
        ("G-SC-OVERRIDES-REASONED", "every override has a reason", "13"),
        ("G-SC-PARITY-COMPLETE", "parity matrix has a row per feature", "13"),
        ("G-SC-REQUIREMENTS-COVER-BUILD", "every built feature maps to a requirement", "13"),
        ("G-SC-UNKNOWNS-DEFAULTED", "every unknown has a V1 default", "13"),
        ("G-SC-CONFLICTS-RESOLVED", "conflicting claims are resolved or explained", "13"),
    ],
    "ARCHITECTURE_LOCKED": _GENERIC
    + [
        ("G-AR-REQUIREMENTS-ADDRESSED", "every requirement is addressed by an ADR", "14"),
        ("G-AR-INFERENCES-PROPOSED", "every inference has a proposed implementation", "14"),
        ("G-AR-INVARIANTS", "invariants exist and are enforced", "14"),
        ("G-AR-REPO-STRUCTURE", "repository structure is declared", "14"),
        ("G-AR-STACK-COMPLETE", "stack fully named", "14"),
        ("G-AR-MANDATORY-TOPICS", "mandatory ADR topics covered", "14"),
    ],
    "PHASE_PLAN_READY": _GENERIC
    + [
        ("G-PP-ROOT-DOCS", "root documents exist with required sections", "15"),
        ("G-PP-PHASE-LINT", "pf.py lint-phases is clean", "15"),
        ("G-PP-TRACE-CLEAN", "pf.py trace reports no errors", "16"),
        ("G-PP-TRACEABILITY-RENDERED", "TRACEABILITY.md matches a fresh render", "16"),
    ],
}

REGISTRY: dict[str, dict[str, GateCondition]] = {stage: {} for stage in EXPECTED}


def register(stage: str, condition: GateCondition) -> None:
    declared = {cid for cid, _, _ in EXPECTED.get(stage, [])}
    if condition.id not in declared:
        raise ValueError(f"{condition.id} is not declared for stage {stage} in gates.EXPECTED")
    REGISTRY[stage][condition.id] = condition


# Modules that register stage-specific conditions; imported lazily on first evaluation so they
# can depend on anything (validators, research, …) without import cycles.
CONDITION_MODULES = (
    "pflib.conditions_discovery",
    "pflib.conditions_product_model",
    "pflib.conditions_scope",
    "pflib.conditions_architecture",
)


def load_conditions() -> None:
    import importlib

    for name in CONDITION_MODULES:
        importlib.import_module(name)


def evaluate(ws: Path, stage: str) -> GateReport:
    load_conditions()
    report = GateReport(stage=stage)
    for cid, description, phase in EXPECTED.get(stage, []):
        cond = REGISTRY.get(stage, {}).get(cid)
        if cond is None:
            row = ResultRow(
                cid, False, STATUS_NOT_BUILT, description, f"not built yet (Phase {phase})"
            )
        else:
            try:
                res = cond.check(ws)
                status = STATUS_PASS if res.passed else STATUS_FAIL
                row = ResultRow(cid, res.passed, status, cond.description, res.detail)
            except PFError as exc:
                row = ResultRow(cid, False, STATUS_ERROR, cond.description, exc.message)
        report.results.append(row)
    return report


# ------------------------------------------------------------- generic conditions


def _state_file_valid(ws: Path) -> ConditionResult:
    from pflib import state

    try:
        state.load(ws)
    except PFError as exc:
        return ConditionResult(False, exc.message)
    return ConditionResult(True, "state.json is valid")


def _no_unmerged_staging(ws: Path) -> ConditionResult:
    root = workspace.staging_root(ws)
    pending = (
        sorted(p.name for p in root.iterdir() if p.is_dir() and p.name not in workspace.ARCHIVES)
        if root.is_dir()
        else []
    )
    if pending:
        return ConditionResult(False, "unmerged staging runs: " + ", ".join(pending))
    return ConditionResult(True, "no unmerged staging runs")


def _scope_set(ws: Path) -> ConditionResult:
    from pflib import state

    scope = state.load(ws).scope
    if not scope.get("text"):
        return ConditionResult(False, "no scope set (pf.py set-scope, or /productforge --scope)")
    if not scope.get("accepted"):
        return ConditionResult(False, f"scope {scope['text']!r} has not been accepted")
    return ConditionResult(True, f"scope: {scope['text']}")


LOCK_CODES = ("LOCK_VIOLATION", "LOCK_DELETED")


def validate_clean(stage: str) -> Callable[[Path], ConditionResult]:
    """No validation errors in the stage's artifacts, and no lock violation anywhere."""

    def check(ws: Path) -> ConditionResult:
        from pflib import validators

        errors = [
            f
            for f in validators.run(ws)
            if f.severity == validators.ERROR
            and (validators.owner_stage(f) == stage or f.code in LOCK_CODES)
        ]
        if errors:
            codes = sorted({f.code for f in errors})
            return ConditionResult(
                False, f"{len(errors)} validation error(s): {', '.join(codes)} (pf.py validate)"
            )
        return ConditionResult(True, "pf.py validate: no errors")

    return check


def _register_generic() -> None:
    for stage in EXPECTED:
        register(
            stage,
            GateCondition(
                "G-STATE-FILE-VALID", "state.json is present and valid", _state_file_valid
            ),
        )
        register(
            stage,
            GateCondition(
                "G-NO-UNMERGED-STAGING",
                "no staging run is waiting to be merged",
                _no_unmerged_staging,
            ),
        )
        register(
            stage,
            GateCondition(
                "G-VALIDATE-CLEAN",
                "pf.py validate reports no errors for this stage",
                validate_clean(stage),
            ),
        )
    register("DISCOVERY", GateCondition("G-SCOPE-SET", "a scope is set and accepted", _scope_set))


_register_generic()
