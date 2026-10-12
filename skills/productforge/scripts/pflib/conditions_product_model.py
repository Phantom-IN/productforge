"""PRODUCT_MODEL exit-gate conditions (IMPLEMENTATION_PLAN.md §7.2). Registered on import."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pflib import domain, records, workflows
from pflib.gates import ConditionResult, GateCondition, register
from pflib.index import WorkspaceIndex

STAGE = "PRODUCT_MODEL"
CORE_DOMAIN_MIN_FEATURES = 3  # a domain with at least this many features needs a workflow
ENTITY_CODES = ("BAD_RELATIONSHIP", "BAD_DELETION_SEMANTICS", "MISSING_FIELD", "EMPTY_FIELD")
PERMISSION_CODES = (
    "PERMISSION_CELL_MISSING", "UNKNOWN_CELL_NO_U", "LIMITED_WITHOUT_MEANS", "BAD_GRANT",
    "ENTITY_WITHOUT_PERMISSIONS", "DUPLICATE_PERMISSION_RULE",
)  # fmt: skip
INFERENCE_FIELDS = ("Observation", "Confidence", "Engineering implication", "Our requirement")


def _sample(ids: list[str], limit: int = 8) -> str:
    return ", ".join(ids[:limit]) + (f" (+{len(ids) - limit} more)" if len(ids) > limit else "")


def _findings(ws: Path, prefixes: tuple[str, ...], codes: tuple[str, ...]) -> list[str]:
    from pflib import ids, validators

    out = []
    for f in validators.run(ws):
        parsed = ids.parse(f.record_id, strict=False) if f.record_id else None
        if f.code in codes and parsed is not None and parsed.prefix in prefixes:
            out.append(f"{f.record_id} {f.code}")
    return sorted(set(out))


def _surface_features(ws: Path) -> ConditionResult:
    index = WorkspaceIndex(ws)
    feats = domain.active(index, "F")
    linked = {ref for f in feats for ref in records.parse_refs(f.get("Surface"))}
    missing = [ps.id for ps in domain.active(index, "PS") if ps.id not in linked]
    if not feats:
        return ConditionResult(False, "no features yet (/productforge features)")
    if missing:
        return ConditionResult(False, f"surfaces without a feature: {_sample(missing)}")
    return ConditionResult(True, f"every surface maps to a feature ({len(feats)} features)")


def _feature_evidence(ws: Path) -> ConditionResult:
    feats = domain.active(WorkspaceIndex(ws), "F")
    bare = [f.id for f in feats if not (f.get("Evidence").strip() or f.get("Derived from").strip())]
    if not feats:
        return ConditionResult(False, "no features yet (/productforge features)")
    if bare:
        return ConditionResult(False, f"features without Evidence or Derived from: {_sample(bare)}")
    return ConditionResult(True, f"all {len(feats)} features cite evidence or are derived")


def _workflow_per_domain(ws: Path) -> ConditionResult:
    index = WorkspaceIndex(ws)
    feats = domain.active(index, "F")
    domain_of = {f.id: f.get("Domain").strip() for f in feats}
    sizes: dict[str, int] = {}
    for d in domain_of.values():
        sizes[d] = sizes.get(d, 0) + 1
    core = sorted(d for d, n in sizes.items() if d and n >= CORE_DOMAIN_MIN_FEATURES)
    covered = {
        domain_of[ref]
        for w in domain.active(index, "W")
        for ref in records.parse_refs(w.get("Features"))
        if ref in domain_of
    }
    missing = [d for d in core if d not in covered]
    if not core:
        return ConditionResult(False, "no core domains yet (/productforge features)")
    if missing:
        return ConditionResult(False, f"core domains without a workflow: {', '.join(missing)} "
                                      "(/productforge workflows)")  # fmt: skip
    return ConditionResult(True, f"all {len(core)} core domains (≥ {CORE_DOMAIN_MIN_FEATURES} "
                                 "features) have a workflow")  # fmt: skip


def _entity_complete(ws: Path) -> ConditionResult:
    ents = domain.active(WorkspaceIndex(ws), "E")
    if not ents:
        return ConditionResult(False, "no entities yet (/productforge model)")
    bad = _findings(ws, ("E",), ENTITY_CODES)
    if bad:
        return ConditionResult(False, f"incomplete entities: {_sample(bad)}")
    return ConditionResult(True, f"{len(ents)} entities with identity, lifecycle and deletion")


def _permissions(ws: Path) -> ConditionResult:
    index = WorkspaceIndex(ws)
    cells = domain.permission_cells(index)
    if not cells["roles"] or not cells["rules"]:
        return ConditionResult(False, "no roles or permission rules yet (/productforge model)")
    bad = _findings(ws, ("E", "PR"), PERMISSION_CODES)
    if bad:
        return ConditionResult(False, f"permission gaps: {_sample(bad)}")
    return ConditionResult(True, f"{cells['rules']} rules × {cells['roles']} roles, "
                                 f"{cells['cells']['?']} unknown cells")  # fmt: skip


def _integrations(ws: Path) -> ConditionResult:
    from pflib import catalog

    found = domain.active(WorkspaceIndex(ws), "I")
    if not found:
        return ConditionResult(False, "no integrations yet (/productforge model, integration pass)")
    allowed = catalog.ENUMS[("I", "Direction")]
    bad = [
        i.id
        for i in found
        if i.get("Direction").strip() not in allowed or not i.get("Authentication").strip()
    ]
    if bad:
        return ConditionResult(
            False, f"integrations missing Direction/Authentication: {_sample(bad)}"
        )
    return ConditionResult(True, f"{len(found)} integrations with direction and authentication")


def _inference(ws: Path) -> ConditionResult:
    index = WorkspaceIndex(ws)
    inferences = domain.active(index, "A")
    if not inferences:
        return ConditionResult(False, "no architecture inferences yet (/productforge model)")
    incomplete = [a.id for a in inferences if any(not a.get(k).strip() for k in INFERENCE_FIELDS)]
    cited = {ref for a in inferences for ref in records.parse_refs(a.get("Derived from"))}
    uncovered = [
        w.id
        for rel, w in index.records("W")
        if records.is_active(w)
        and workflows.has_system_steps(index.document(rel).text)
        and w.id not in cited
    ]
    problems = []
    if incomplete:
        problems.append(f"incomplete inferences: {_sample(incomplete)}")
    if uncovered:
        problems.append(f"workflows with implied-system steps but no A record: "
                        f"{_sample(sorted(uncovered))}")  # fmt: skip
    if problems:
        return ConditionResult(False, "; ".join(problems))
    return ConditionResult(True, f"{len(inferences)} inferences; every workflow with system steps "
                                 "is covered")  # fmt: skip


CONDITIONS: tuple[tuple[str, str, Callable[[Path], ConditionResult]], ...] = (
    ("G-PM-SURFACE-FEATURES", "every product surface maps to a feature", _surface_features),
    ("G-PM-FEATURE-EVIDENCE", "every feature cites evidence or is derived", _feature_evidence),
    ("G-PM-WORKFLOW-PER-DOMAIN", "every core domain has a workflow", _workflow_per_domain),
    ("G-PM-ENTITY-COMPLETE", "entities have identity, lifecycle, deletion semantics",
     _entity_complete),
    ("G-PM-PERMISSIONS-COVERAGE", "mutable entities have permission rules", _permissions),
    ("G-PM-INTEGRATIONS-COMPLETE", "integrations have direction and authentication",
     _integrations),
    ("G-PM-INFERENCE-COMPLETE", "architecture inferences are complete", _inference),
)  # fmt: skip

for _cid, _desc, _fn in CONDITIONS:
    register(STAGE, GateCondition(_cid, _desc, _fn))
