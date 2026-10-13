"""SCOPE_DEFINED exit-gate conditions (IMPLEMENTATION_PLAN.md §7.2). Registered on import."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pflib import catalog, domain, records, render, score
from pflib.gates import ConditionResult, GateCondition, register
from pflib.index import WorkspaceIndex

STAGE = "SCOPE_DEFINED"
SCOPE_VIEWS = (catalog.FEATURE_MATRIX_PATH, catalog.PARITY_PATH, catalog.PRODUCT_SPEC_PATH)


def _sample(ids: list[str], limit: int = 8) -> str:
    return ", ".join(ids[:limit]) + (f" (+{len(ids) - limit} more)" if len(ids) > limit else "")


def _all_scored(ws: Path) -> ConditionResult:
    index = WorkspaceIndex(ws)
    feats = [f.id for f in domain.active(index, "F")]
    cards: dict[str, int] = {}
    for sc in domain.active(index, "SC"):
        for fid in records.parse_refs(sc.get("Feature")):
            cards[fid] = cards.get(fid, 0) + 1
    missing = [f for f in feats if f not in cards]
    doubled = sorted(f for f, n in cards.items() if n > 1)
    if not feats:
        return ConditionResult(False, "no features to score")
    if missing or doubled:
        parts = [f"unscored: {_sample(missing)}"] if missing else []
        parts += [f"scored twice: {_sample(doubled)}"] if doubled else []
        return ConditionResult(False, "; ".join(parts))
    return ConditionResult(True, f"all {len(feats)} features have one score card")


def _decisions_computed(ws: Path) -> ConditionResult:
    rows = score.evaluate(ws)
    malformed = [r.sc for r in rows if r.priority is None]
    index = WorkspaceIndex(ws)
    stale = [
        rel
        for rel in SCOPE_VIEWS
        if (ws / rel).is_file()
        and render.render_text(rel, (ws / rel).read_text(encoding="utf-8"), index)
        != (ws / rel).read_text(encoding="utf-8")
    ]
    if malformed:
        return ConditionResult(False, f"score cards with malformed scores: {_sample(malformed)}")
    if stale:
        return ConditionResult(False, f"views differ from a fresh pf.py score: {', '.join(stale)} "
                                      "(pf.py score --write)")  # fmt: skip
    if not rows:
        return ConditionResult(False, "no score cards yet (/productforge scope)")
    return ConditionResult(True, f"{len(rows)} decisions match a fresh pf.py score run")


def _overrides_reasoned(ws: Path) -> ConditionResult:
    index = WorkspaceIndex(ws)
    bare = [
        sc.id
        for sc in domain.active(index, "SC")
        if sc.get("Override decision").strip() and not sc.get("Override reason").strip()
    ]
    n = sum(1 for sc in domain.active(index, "SC") if sc.get("Override decision").strip())
    if bare:
        return ConditionResult(False, f"overrides without a reason: {_sample(bare)}")
    return ConditionResult(True, f"{n} overrides, all with reasons")


def _parity_complete(ws: Path) -> ConditionResult:
    path = ws / catalog.PARITY_PATH
    if not path.is_file():
        return ConditionResult(False, f"{catalog.PARITY_PATH} does not exist yet")
    body = render.regions(path.read_text(encoding="utf-8")).get("parity", "")
    listed = {line.split(" ", 2)[1] for line in body.splitlines() if line.startswith("| F-")}
    feats = [f.id for f in domain.active(WorkspaceIndex(ws), "F")]
    missing = [f for f in feats if f not in listed]
    if missing:
        return ConditionResult(False, f"parity matrix lacks rows for: {_sample(missing)}")
    return ConditionResult(True, f"parity matrix has a row for all {len(feats)} features")


def _requirements_cover_build(ws: Path) -> ConditionResult:
    index = WorkspaceIndex(ws)
    covered = {
        ref for r in domain.active(index, "R") for ref in records.parse_refs(r.get("Features"))
    }
    built = [r.feature for r in score.evaluate(ws, index) if r.decision in score.IN_V1]
    missing = [f for f in built if f not in covered]
    if not built:
        return ConditionResult(False, "no feature is built in V1 yet")
    if missing:
        return ConditionResult(False, f"V1 features without a requirement: {_sample(missing)}")
    return ConditionResult(True, f"all {len(built)} V1 features are covered by requirements")


def _unknowns_defaulted(ws: Path) -> ConditionResult:
    index = WorkspaceIndex(ws)
    defaulted = {
        ref for ud in domain.active(index, "UD") for ref in records.parse_refs(ud.get("Unknown"))
    }
    missing = [u.id for u in domain.active(index, "U")
               if u.id not in defaulted and not u.get("V1 default").strip()]  # fmt: skip
    if missing:
        return ConditionResult(False, f"unknowns without a V1 default: {_sample(missing)}")
    return ConditionResult(True, "every unknown has a V1 default")


def _conflicts_resolved(ws: Path) -> ConditionResult:
    from pflib import validators

    open_ = sorted(
        {f.record_id or "?" for f in validators.run(ws) if f.code == "CONFLICT_UNRESOLVED"}
    )
    if open_:
        return ConditionResult(False, f"conflicting claims with no explanation: {_sample(open_)}")
    return ConditionResult(True, "every conflict is resolved or explained")


CONDITIONS: tuple[tuple[str, str, Callable[[Path], ConditionResult]], ...] = (
    ("G-SC-ALL-SCORED", "every feature has a score card", _all_scored),
    ("G-SC-DECISIONS-COMPUTED", "decisions match a fresh pf.py score run", _decisions_computed),
    ("G-SC-OVERRIDES-REASONED", "every override has a reason", _overrides_reasoned),
    ("G-SC-PARITY-COMPLETE", "parity matrix has a row per feature", _parity_complete),
    ("G-SC-REQUIREMENTS-COVER-BUILD", "every built feature maps to a requirement",
     _requirements_cover_build),
    ("G-SC-UNKNOWNS-DEFAULTED", "every unknown has a V1 default", _unknowns_defaulted),
    ("G-SC-CONFLICTS-RESOLVED", "conflicting claims are resolved or explained",
     _conflicts_resolved),
)  # fmt: skip

for _cid, _desc, _fn in CONDITIONS:
    register(STAGE, GateCondition(_cid, _desc, _fn))
