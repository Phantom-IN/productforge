"""Competitor checks (IMPLEMENTATION_PLAN.md §13): signals need evidence and enough competitors,
complaints come from reviews and forums, and competitor sources never support target claims."""

from __future__ import annotations

from pflib import competitors, confidence, config, records
from pflib.validators import Context, Finding, Loc, finding, record_check, workspace_check

COMPLAINT_TIERS = (3, 4)


def _competitor_sources(ctx: Context) -> dict[str, str]:
    """Competitor S ID → its C ID (cached per run)."""
    if "competitor_sources" not in ctx.cache:
        ctx.cache["competitor_sources"] = {
            loc.record.id: c
            for loc in ctx.records("S")
            if (c := competitors.competitor_of(loc.record)) is not None
        }
    found: dict[str, str] = ctx.cache["competitor_sources"]
    return found


@record_check("FS")
def feature_signal(ctx: Context, loc: Loc) -> list[Finding]:
    rec = loc.record
    if not records.is_active(rec):
        return []
    signal = rec.get("Signal").strip()
    feats = [r for r in records.parse_refs(rec.get("Feature")) if r.startswith("F-")]
    comps = [c for c in records.parse_refs(rec.get("Competitors"))
             if (loc_c := ctx.get(c)) is not None and records.is_active(loc_c.record)]  # fmt: skip
    out: list[Finding] = []
    if signal == competitors.ABSENT and feats:
        msg = (f"{rec.id}: an absent-in-target signal names a capability the target lacks, so "
               f"its Feature cannot be a target feature ({', '.join(feats)})")  # fmt: skip
        out.append(finding("BAD_FEATURE_SIGNAL", loc.rel, rec.id, msg))
    elif signal in competitors.SIGNALS and signal != competitors.ABSENT and len(feats) != 1:
        msg = f"{rec.id}: a {signal} signal's Feature must be exactly one F ID"
        out.append(finding("BAD_FEATURE_SIGNAL", loc.rel, rec.id, msg))
    if signal == "table-stakes" and len(comps) < competitors.TABLE_STAKES_MIN:
        out.append(finding("TABLE_STAKES_UNDERSUPPORTED", loc.rel, rec.id,
                           f"{rec.id}: table-stakes needs ≥ {competitors.TABLE_STAKES_MIN} "
                           f"competitors (has {len(comps)})"))  # fmt: skip
    if signal == "rare" and len(comps) != 1:
        out.append(finding("BAD_FEATURE_SIGNAL", loc.rel, rec.id,
                           f"{rec.id}: a rare signal names exactly one competitor"))  # fmt: skip
    return out


@record_check("C")
def complaints(ctx: Context, loc: Loc) -> list[Finding]:
    rec = loc.record
    text = rec.get("Common complaints").strip()
    if not text or text.lower().startswith("none"):
        return []
    refs = records.parse_refs(text)
    bad = []
    for ref in refs:
        src = ctx.get(ref)
        tier = confidence.parse_tier(src.record.get("Tier")) if src else None
        if src is not None and tier not in COMPLAINT_TIERS:
            bad.append(f"{ref} (Tier {tier})")
    if not refs or bad:
        why = "cite no source" if not refs else f"cite {', '.join(bad)}"
        return [finding("COMPLAINT_SOURCE_TIER", loc.rel, rec.id,
                        f"{rec.id}: common complaints {why}; they come from Tier 3–4 reviews and "
                        "forums, paraphrased")]  # fmt: skip
    return []


@record_check("S")
def competitor_area(ctx: Context, loc: Loc) -> list[Finding]:
    cid = competitors.competitor_of(loc.record)
    if cid is None or ctx.get(cid) is not None:
        return []
    msg = f"{loc.record.id}.Relevant area names {cid}, which does not exist"
    return [finding("DANGLING_REF", loc.rel, loc.record.id, msg)]


@workspace_check
def source_budget(ctx: Context) -> list[Finding]:
    budget = int(config.resolve("competitors.max_sources", ctx.ws))
    per: dict[str, list[str]] = {}
    for sid, cid in _competitor_sources(ctx).items():
        per.setdefault(cid, []).append(sid)
    out: list[Finding] = []
    for cid, sids in sorted(per.items()):
        loc = ctx.get(cid)
        if loc is not None and len(sids) > budget:
            msg = (f"{cid} has {len(sids)} sources (budget {budget}, competitors.max_sources): "
                   "competitors are researched shallowly")  # fmt: skip
            out.append(finding("COMPETITOR_OVER_BUDGET", loc.rel, cid, msg))
    return out


@record_check()
def target_evidence_is_not_competitor_evidence(ctx: Context, loc: Loc) -> list[Finding]:
    assert loc.schema is not None
    if loc.schema.prefix in ("C", "FS", "S") or "Evidence" not in loc.record.fields:
        return []
    theirs = _competitor_sources(ctx)
    cited = [r for r in records.parse_refs(loc.record.get("Evidence")) if r in theirs]
    if not cited:
        return []
    return [finding("COMPETITOR_SOURCE_AS_EVIDENCE", loc.rel, loc.record.id,
                    f"{loc.record.id} cites competitor sources {', '.join(cited)}; they describe "
                    "another product and support only C/FS records")]  # fmt: skip
