"""Feature prioritisation (IMPLEMENTATION_PLAN.md §14, ``references/prioritisation-model.md``).

The scope-editor scores each feature 0–3 per criterion with a rationale (``SC`` records); this
module does **all** the arithmetic and applies the decision rules. Pure functions, no I/O except
``evaluate`` (which reads the workspace through ``WorkspaceIndex``).

    priority = Σ w·s (benefits) − Σ w·s (costs) [+ table-stakes bonus]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from pflib import config, records

# SC field → (weight config key, +1 benefit / -1 cost)
CRITERIA: dict[str, tuple[str, int]] = {
    "Core value": ("scope.weights.core_value", 1),
    "User frequency": ("scope.weights.user_frequency", 1),
    "Dependency importance": ("scope.weights.dependency_importance", 1),
    "Differentiation": ("scope.weights.differentiation", 1),
    "Engineering complexity": ("scope.weights.engineering_complexity", -1),
    "Infrastructure complexity": ("scope.weights.infrastructure_complexity", -1),
    "Security impact": ("scope.weights.security_impact", -1),
    "Operational cost": ("scope.weights.operational_cost", -1),
    "Time to implement": ("scope.weights.time_to_implement", -1),
}
EXTERNAL = "External availability"  # modifies the decision, not the score
SCORED_FIELDS = (*CRITERIA, EXTERNAL)

BUILD_NOW = "BUILD NOW"
BUILD_SIMPLIFIED = "BUILD SIMPLIFIED"
USE_EXTERNAL = "USE EXTERNAL SERVICE"
DEFER = "DEFER"
DROP = "DROP"
DECISIONS = (BUILD_NOW, BUILD_SIMPLIFIED, USE_EXTERNAL, DEFER, DROP)
IN_V1 = (BUILD_NOW, BUILD_SIMPLIFIED, USE_EXTERNAL)

TABLE_STAKES_BONUS = 2.0  # added when ≥ 2 competitors offer the feature (Phase 12 signals)
TABLE_STAKES_MIN = 2

SCORE_RE = re.compile(r"^(?P<n>[0-3])\s*[—–-]\s*(?P<why>\S.*)$", re.S)


def parse_score(value: str) -> tuple[int | None, str]:
    """``"3 — every flow starts here"`` → (3, rationale); malformed → (None, "")."""
    m = SCORE_RE.match(value.strip())
    if not m:
        return None, ""
    return int(m.group("n")), m.group("why").strip()


@dataclass(frozen=True)
class Thresholds:
    build: float
    defer: float


def weights(ws: Path | None = None) -> dict[str, float]:
    return {name: float(config.resolve(key, ws)) for name, (key, _) in CRITERIA.items()}


def thresholds(ws: Path | None = None) -> Thresholds:
    return Thresholds(
        float(config.resolve("scope.build_threshold", ws)),
        float(config.resolve("scope.defer_threshold", ws)),
    )


def priority(scores: dict[str, int], w: dict[str, float], table_stakes: int = 0) -> float:
    total = sum(w[name] * sign * scores[name] for name, (_, sign) in CRITERIA.items())
    if table_stakes >= TABLE_STAKES_MIN:
        total += TABLE_STAKES_BONUS
    return float(total)


def decide(scores: dict[str, int], prio: float, t: Thresholds) -> tuple[str, str]:
    """(decision, rule) for parsed scores and a computed priority — ordered rules, then the
    dependency floor: a feature others depend on is never deferred or dropped."""
    eng = scores["Engineering complexity"]
    if scores[EXTERNAL] == 3 and eng >= 2:
        decision, rule = USE_EXTERNAL, "R2 external service available, complex to build"
    elif prio >= t.build and eng == 3:
        decision, rule = BUILD_SIMPLIFIED, "R3 above build threshold, highest complexity"
    elif prio >= t.build:
        decision, rule = BUILD_NOW, "R4 above build threshold"
    elif prio >= t.defer:
        decision, rule = DEFER, "R5 above defer threshold"
    else:
        decision, rule = DROP, "R6 below defer threshold"
    if scores["Dependency importance"] == 3 and decision in (DEFER, DROP):
        decision = BUILD_SIMPLIFIED if eng >= 2 else BUILD_NOW
        rule = "R1 dependency floor: other features need it"
    return decision, rule


@dataclass(frozen=True)
class Row:
    sc: str
    feature: str
    priority: float | None
    computed: str | None  # None when a score is malformed
    decision: str | None  # final: the override when one is set, else computed
    rule: str
    override: str | None
    table_stakes: int
    engineering: int | None = None  # Engineering complexity, for the parent floor

    def to_dict(self) -> dict[str, Any]:
        return {
            "sc": self.sc,
            "feature": self.feature,
            "priority": self.priority,
            "computed": self.computed,
            "decision": self.decision,
            "rule": self.rule,
            "override": self.override,
            "table_stakes": self.table_stakes,
        }


def score_record(
    sc: records.Record, w: dict[str, float], t: Thresholds, stakes: dict[str, int]
) -> Row:
    feature = next(iter(records.parse_refs(sc.get("Feature"))), "")
    parsed = {name: parse_score(sc.get(name))[0] for name in SCORED_FIELDS}
    override = sc.get("Override decision").strip() or None
    n_stakes = stakes.get(feature, 0)
    if any(v is None for v in parsed.values()):
        bad = ", ".join(k for k, v in parsed.items() if v is None)
        return Row(sc.id, feature, None, None, override, f"malformed scores: {bad}", override,
                   n_stakes)  # fmt: skip
    scores = {k: v for k, v in parsed.items() if v is not None}
    prio = priority(scores, w, n_stakes)
    computed, rule = decide(scores, prio, t)
    return Row(sc.id, feature, prio, computed, override or computed, rule, override, n_stakes,
               scores["Engineering complexity"])  # fmt: skip


def parent_floor(rows: list[Row], parents: dict[str, str]) -> list[Row]:
    """R1 parent floor (v1.1 dogfood: sub-features landed in V1 under a deferred parent): a
    DEFER/DROP parent of a V1 feature is built — BUILD SIMPLIFIED if Engineering complexity ≥ 2,
    else BUILD NOW — up the chain until nothing changes. A user's override always wins."""
    by_feature = {r.feature: r for r in rows}
    changed = True
    while changed:
        changed = False
        for feature, parent in sorted(parents.items()):
            child, up = by_feature.get(feature), by_feature.get(parent)
            if child is None or up is None or child.decision not in IN_V1:
                continue
            if up.override is not None or up.decision not in (DEFER, DROP):
                continue
            kids = sorted(
                f for f, p in parents.items()
                if p == parent and f in by_feature and by_feature[f].decision in IN_V1
            )  # fmt: skip
            decision = BUILD_SIMPLIFIED if (up.engineering or 0) >= 2 else BUILD_NOW
            rule = f"R1 parent floor: {', '.join(kids)} in V1 need it"
            by_feature[parent] = replace(up, computed=decision, decision=decision, rule=rule)
            changed = True
    return [by_feature.get(r.feature, r) for r in rows]


def evaluate(ws: Path, index: Any = None) -> list[Row]:
    """A row per active SC record, in feature order."""
    from pflib import competitors
    from pflib.index import WorkspaceIndex

    index = index or WorkspaceIndex(ws)
    w, t = weights(ws), thresholds(ws)
    stakes = competitors.table_stakes(index)
    rows = [
        score_record(sc, w, t, stakes) for _, sc in index.records("SC") if records.is_active(sc)
    ]
    parents = {}
    for _, f in index.records("F"):
        if records.is_active(f):
            refs = [r for r in records.parse_refs(f.get("Parent")) if r.startswith("F-")]
            if refs:
                parents[f.id] = refs[0]
    return sorted(parent_floor(rows, parents), key=lambda r: (r.feature, r.sc))


def report(ws: Path) -> dict[str, Any]:
    rows = evaluate(ws)
    counts = dict.fromkeys(DECISIONS, 0)
    for r in rows:
        if r.decision in counts:
            counts[r.decision] += 1
    t = thresholds(ws)
    return {
        "rows": [r.to_dict() for r in rows],
        "counts": counts,
        "overrides": [r.to_dict() for r in rows if r.override],
        "thresholds": {"build": t.build, "defer": t.defer},
    }


# ------------------------------------------------------------------ user overrides


def record_override(ws: Path, feature: str, decision: str | None, reason: str) -> dict[str, Any]:
    """Record the user's decision for a feature as a logged amendment of its score card, through
    a staging run and ``merge`` (the only writer). ``decision=None`` clears the override."""
    from pflib import catalog, merge, workspace
    from pflib.errors import UsageError
    from pflib.index import WorkspaceIndex

    if decision is not None and decision not in DECISIONS:
        raise UsageError(f"decision must be one of {', '.join(DECISIONS)}", code="BAD_DECISION")
    if not reason.strip():
        raise UsageError("an override needs --reason (the user's words)", code="OVERRIDE_NO_REASON")
    cards = [
        sc
        for _, sc in WorkspaceIndex(ws).records("SC")
        if records.is_active(sc) and feature in records.parse_refs(sc.get("Feature"))
    ]
    if len(cards) != 1:
        raise UsageError(f"{feature} has {len(cards)} active score cards (need exactly one)",
                         code="NO_SCORE_CARD")  # fmt: skip
    sc = cards[0]
    text = (
        f"### AMEND {sc.id}\n- Override decision: {decision or ''}\n"
        f"- Override reason: {reason.strip() if decision else ''}\n"
        f"- Why: {'user override' if decision else 'override cleared by the user'}: "
        f"{reason.strip()}\n"
    )
    run_id, path = workspace.create_staging_run(ws, "user-override")
    (path / catalog.PARITY_PATH).parent.mkdir(parents=True, exist_ok=True)
    (path / catalog.PARITY_PATH).write_text(text, encoding="utf-8")
    report = merge.merge(ws, run_id)
    row = next(r for r in evaluate(ws) if r.sc == sc.id)
    return {"sc": sc.id, "feature": feature, "computed": row.computed, "decision": row.decision,
            "override": row.override, "run_id": run_id, "rendered": report.rendered}  # fmt: skip
