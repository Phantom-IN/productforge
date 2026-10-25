"""Scope checks: honest score cards, reasoned overrides, decisions
that carry their details, and requirements for everything we build."""

from __future__ import annotations

import re

from pflib import catalog, config, features, records, score
from pflib.validators import Context, Finding, Loc, finding, record_check, workspace_check


def _active(ctx: Context, prefix: str) -> list[Loc]:
    return [loc for loc in ctx.records(prefix) if records.is_active(loc.record)]


def _rows(ctx: Context) -> dict[str, score.Row]:
    """SC ID → computed row (cached per validation run)."""
    if "score_rows" not in ctx.cache:
        ctx.cache["score_rows"] = {r.sc: r for r in score.evaluate(ctx.ws)}
    rows: dict[str, score.Row] = ctx.cache["score_rows"]
    return rows


def _headline(ctx: Context) -> set[str]:
    if "headline" not in ctx.cache:
        ctx.cache["headline"] = features.headline_features(ctx.ws)
    headline: set[str] = ctx.cache["headline"]
    return headline


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
    if row and row.computed in (score.DEFER, score.DROP) and row.override is None:
        if row.feature in _headline(ctx):
            msg = (
                f"{row.feature} is marketed by the target (headline) but computes {row.computed}; "
                "review it and record an override (any decision) with the reason"
            )
            out.append(finding("HEADLINE_FEATURE_CUT", loc.rel, rec.id, msg))
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


_SOURCE_ID_RE = re.compile(r"\b(?:S|D|U)-\d+\b")


def regulatory_pattern(terms: list[str]) -> re.Pattern[str] | None:
    """Words of ``quality.regulatory_terms``: terms of 6+ letters match as a prefix (statut →
    statutory, regulation → regulations); shorter ones as whole words, optionally plural."""
    parts = [
        re.escape(t) + r"\w*" if len(t) >= 6 else re.escape(t) + r"(?:s|es)?\b"
        for t in (x.strip().lower() for x in terms)
        if t
    ]
    return re.compile(r"\b(?:" + "|".join(parts) + ")", re.I) if parts else None


@workspace_check
def default_rule_unsourced(ctx: Context) -> list[Finding]:
    """A regulatory number in an accepted default (a law, a deadline, a tax) needs a source."""
    entry = ctx.docs.get(catalog.PRODUCT_SPEC_PATH)
    if entry is None:
        return []
    pattern = regulatory_pattern(list(config.resolve("quality.regulatory_terms", ctx.ws)))
    if pattern is None:
        return []
    out: list[Finding] = []
    for line in (entry[1].section_text("Accepted defaults") or "").splitlines():
        text = line.strip()
        if not text or text.startswith(("<!--", "_")) or re.match(r"^\|\s*:?-{3}", text):
            continue
        if text.startswith("|"):  # generated rows: the first cell is the unknown's own ID
            cells = [c.strip() for c in text.strip("|").split("|")]
            if cells[:1] == ["Unknown"]:
                continue  # the header row
            text = " | ".join(cells[1:])
        if pattern.search(text) and re.search(r"\d", text) and not _SOURCE_ID_RE.search(text):
            msg = (
                f"accepted default {text[:80]!r} states a regulatory number but cites no S, D or U "
                "record; cite the source that fixes it (a statutory period needs its source)"
            )
            out.append(finding("DEFAULT_RULE_UNSOURCED", catalog.PRODUCT_SPEC_PATH, None, msg))
    return out
