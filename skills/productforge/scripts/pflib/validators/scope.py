"""Scope checks: honest score cards, reasoned overrides, decisions
that carry their details, and requirements for everything we build."""

from __future__ import annotations

from pflib import catalog, records, score
from pflib.validators import Context, Finding, Loc, finding, record_check, workspace_check


def _active(ctx: Context, prefix: str) -> list[Loc]:
    return [loc for loc in ctx.records(prefix) if records.is_active(loc.record)]


def _rows(ctx: Context) -> dict[str, score.Row]:
    """SC ID → computed row (cached per validation run)."""
    if "score_rows" not in ctx.cache:
        ctx.cache["score_rows"] = {r.sc: r for r in score.evaluate(ctx.ws)}
    rows: dict[str, score.Row] = ctx.cache["score_rows"]
    return rows


@record_check("SC")
def score_card(ctx: Context, loc: Loc) -> list[Finding]:
    rec = loc.record
    if not records.is_active(rec):
        return []
    out: list[Finding] = []
    for name in score.SCORED_FIELDS:
        value = rec.get(name)
        if value.strip() and score.parse_score(value)[0] is None:
            msg = f"{rec.id}.{name} is {value.strip()!r}; write '<0-3> — <rationale>'"
            out.append(finding("BAD_SCORE", loc.rel, rec.id, msg))
    if rec.get("Override decision").strip() and not rec.get("Override reason").strip():
        msg = f"{rec.id} overrides the computed decision without an 'Override reason'"
        out.append(finding("OVERRIDE_NO_REASON", loc.rel, rec.id, msg))
    row = _rows(ctx).get(rec.id)
    decision = row.decision if row else None
    if decision == score.BUILD_SIMPLIFIED and not rec.get("Simplification").strip():
        msg = f"{rec.id} is BUILD SIMPLIFIED; say what V1 leaves out in 'Simplification'"
        out.append(finding("SIMPLIFICATION_MISSING", loc.rel, rec.id, msg))
    if decision == score.USE_EXTERNAL and not rec.get("External service").strip():
        msg = f"{rec.id} is USE EXTERNAL SERVICE; name the kind of service in 'External service'"
        out.append(finding("EXTERNAL_SERVICE_MISSING", loc.rel, rec.id, msg))
    return out


@workspace_check
def every_feature_scored_once(ctx: Context) -> list[Finding]:
    if catalog.PARITY_PATH not in ctx.docs:
        return []  # scoring has not started (SCOPE_DEFINED)
    by_feature: dict[str, list[str]] = {}
    for loc in _active(ctx, "SC"):
        for fid in records.parse_refs(loc.record.get("Feature")):
            by_feature.setdefault(fid, []).append(loc.record.id)
    out: list[Finding] = []
    unscored = [loc.record.id for loc in _active(ctx, "F") if loc.record.id not in by_feature]
    if unscored:
        shown = ", ".join(unscored[:10]) + (" …" if len(unscored) > 10 else "")
        msg = f"{len(unscored)} features have no score card: {shown}"
        out.append(finding("FEATURE_UNSCORED", catalog.PARITY_PATH, None, msg))
    for fid, scs in sorted(by_feature.items()):
        if len(scs) > 1:
            msg = f"{fid} has {len(scs)} active score cards ({', '.join(scs)}); keep one"
            out.append(finding("DUPLICATE_SCORE", catalog.PARITY_PATH, scs[1], msg))
    return out


@workspace_check
def builds_have_requirements(ctx: Context) -> list[Finding]:
    reqs = _active(ctx, "R")
    if not reqs:
        return []  # requirements come in the second scope pass
    covered = {ref for loc in reqs for ref in records.parse_refs(loc.record.get("Features"))}
    out: list[Finding] = []
    for row in _rows(ctx).values():
        if row.decision in score.IN_V1 and row.feature not in covered:
            msg = f"{row.feature} is {row.decision} but no requirement lists it under Features"
            out.append(finding("FEATURE_WITHOUT_REQUIREMENT", catalog.PRODUCT_SPEC_PATH, row.sc,
                               msg))  # fmt: skip
    return out
