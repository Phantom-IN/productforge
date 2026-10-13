"""ARCHITECTURE_LOCKED exit-gate conditions (IMPLEMENTATION_PLAN.md §7.2). Registered on import."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pflib import architecture, catalog, domain
from pflib.gates import ConditionResult, GateCondition, register
from pflib.index import WorkspaceIndex

STAGE = "ARCHITECTURE_LOCKED"
NO_DOC = ConditionResult(
    False, f"{catalog.ARCHITECTURE_PATH} does not exist yet (/productforge architect)"
)


def _sample(ids: list[str], limit: int = 8) -> str:
    return ", ".join(ids[:limit]) + (f" (+{len(ids) - limit} more)" if len(ids) > limit else "")


def _requirements(ws: Path) -> ConditionResult:
    if architecture.text_of(ws) is None:
        return NO_DOC
    cov = architecture.coverage(ws)
    if not cov.by_requirement:
        return ConditionResult(False, "no requirements to address")
    if cov.unaddressed:
        return ConditionResult(False, f"requirements not addressed: {_sample(cov.unaddressed)}")
    by_convention = sum(1 for v in cov.by_requirement.values() if v == ["convention"])
    return ConditionResult(True, f"all {len(cov.by_requirement)} requirements addressed "
                                 f"({by_convention} by convention)")  # fmt: skip


def _inferences(ws: Path) -> ConditionResult:
    if architecture.text_of(ws) is None:
        return NO_DOC
    cov = architecture.coverage(ws)
    bad = cov.unproposed + cov.multi_proposed
    if bad:
        return ConditionResult(False, f"inferences without exactly one proposal: {_sample(bad)}")
    n = len(domain.active(WorkspaceIndex(ws), "A"))
    return ConditionResult(True, f"all {n} inferences have a proposal")


def _invariants(ws: Path) -> ConditionResult:
    invs = domain.active(WorkspaceIndex(ws), "INV")
    bare = [i.id for i in invs if architecture.enforcement_kind(i.get("Enforced by")) is None]
    if not invs:
        return ConditionResult(False, "no invariants yet")
    if bare:
        return ConditionResult(False, f"invariants without a mechanism: {_sample(bare)}")
    return ConditionResult(True, f"{len(invs)} invariants, all enforced")


def _repo(ws: Path) -> ConditionResult:
    text = architecture.text_of(ws)
    if text is None:
        return NO_DOC
    paths, error = architecture.tree(text)
    if error:
        return ConditionResult(False, f"repository structure: {error}")
    return ConditionResult(True, f"repository structure declares {len(paths)} paths")


def _stack(ws: Path) -> ConditionResult:
    text = architecture.text_of(ws)
    if text is None:
        return NO_DOC
    rows = architecture.stack_rows(text)
    bad = [r[0] for r in rows if len(r) < 2 or architecture.INCOMPLETE_RE.match(r[1])]
    if not rows:
        return ConditionResult(False, "no stack table")
    if bad:
        return ConditionResult(False, f"stack choices still open: {', '.join(bad)}")
    return ConditionResult(True, f"stack fully named ({len(rows)} concerns)")


def _topics(ws: Path) -> ConditionResult:
    if architecture.text_of(ws) is None:
        return NO_DOC
    missing = architecture.coverage(ws).topics_missing
    if missing:
        return ConditionResult(False, f"mandatory topics not decided: {', '.join(missing)}")
    return ConditionResult(True, f"all {len(architecture.MANDATORY_TOPICS)} mandatory topics "
                                 "decided or explained")  # fmt: skip


CONDITIONS: tuple[tuple[str, str, Callable[[Path], ConditionResult]], ...] = (
    ("G-AR-REQUIREMENTS-ADDRESSED", "every requirement is addressed by an ADR", _requirements),
    ("G-AR-INFERENCES-PROPOSED", "every inference has a proposed implementation", _inferences),
    ("G-AR-INVARIANTS", "invariants exist and are enforced", _invariants),
    ("G-AR-REPO-STRUCTURE", "repository structure is declared", _repo),
    ("G-AR-STACK-COMPLETE", "stack fully named", _stack),
    ("G-AR-MANDATORY-TOPICS", "mandatory ADR topics covered", _topics),
)

for _cid, _desc, _fn in CONDITIONS:
    register(STAGE, GateCondition(_cid, _desc, _fn))
