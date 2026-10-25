"""Registers the confidence rules and the conflict protocol as validators."""

from __future__ import annotations

from pflib import confidence, records, urls
from pflib.records import Record
from pflib.validators import Context, Finding, Loc, finding, record_check, workspace_check


def source_index(ctx: Context) -> confidence.SourceIndex:
    if "source_index" not in ctx.cache:

        def tier_of(rec: Record) -> int | None:
            return confidence.parse_tier(rec.get("Tier"))

        def domain_of(rec: Record) -> str:
            return urls.registrable_domain(urls.host_of(rec.get("Canonical URL") or rec.get("URL")))

        records_ = [loc.record for loc in ctx.records()]
        ctx.cache["source_index"] = confidence.build_index(records_, tier_of, domain_of)
    index: confidence.SourceIndex = ctx.cache["source_index"]
    return index


@record_check()
def confidence_rules(ctx: Context, loc: Loc) -> list[Finding]:
    if not records.is_active(loc.record):
        return []  # superseded or rejected records stay in the file, out of every rule
    return [
        finding(v.code, loc.rel, loc.record.id, f"{loc.record.id}: {v.message}")
        for v in confidence.check_record(loc.record, source_index(ctx))
    ]


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


@workspace_check
def conflicts(ctx: Context) -> list[Finding]:
    out: list[Finding] = []
    unknown_refs = [
        set(records.parse_refs(loc.record.get("Related")))
        | set(records.parse_refs(loc.record.get("Available evidence")))
        for loc in ctx.records("U")
    ]
    reported: set[tuple[str, str]] = set()
    for loc in ctx.records():
        rec = loc.record
        for partner_id in confidence.conflict_partners(rec):
            partner = ctx.get(partner_id)
            if partner is None:
                continue  # reported as DANGLING_REF
            if rec.id not in confidence.conflict_partners(partner.record):
                out.append(
                    finding(
                        "CONFLICT_ASYMMETRIC",
                        loc.rel,
                        rec.id,
                        f"{rec.id} conflicts with {partner_id}, but {partner_id} does "
                        f"not declare the conflict back",
                    )
                )
                continue
            pair = (min(rec.id, partner_id), max(rec.id, partner_id))
            if pair in reported:
                continue
            reported.add(pair)
            ctx_a, ctx_b = _norm(rec.get("Context")), _norm(partner.record.get("Context"))
            for side, side_ctx in ((rec, ctx_a), (partner.record, ctx_b)):
                if not side_ctx:
                    out.append(
                        finding(
                            "CONFLICT_CONTEXT_MISSING",
                            loc.rel,
                            side.id,
                            f"{side.id} is in a conflict with "
                            f"{pair[1] if side.id == pair[0] else pair[0]} but has no Context; "
                            f"name the workflow, feature, screen or setting the claim is about",
                        )
                    )
            has_resolution = bool(
                rec.get("Resolution").strip() or partner.record.get("Resolution").strip()
            )
            if ctx_a and ctx_b and ctx_a != ctx_b and not has_resolution:
                first, second = (
                    (rec, partner.record) if rec.id == pair[0] else (partner.record, rec)
                )
                out.append(
                    finding(
                        "CONFLICT_CONTEXT_DIFFERS",
                        loc.rel,
                        pair[0],
                        f"{pair[0]} ({first.get('Context')}) and {pair[1]} "
                        f"({second.get('Context')})"
                        f" are about different contexts, so this is probably not a conflict; "
                        f"add 'Resolution: different contexts — <why>' or fix a Context",
                    )
                )
            resolved = bool(
                rec.get("Resolution").strip() or partner.record.get("Resolution").strip()
            )
            explained = any(set(pair) <= refs for refs in unknown_refs)
            if not (resolved or explained):
                out.append(
                    finding(
                        "CONFLICT_UNRESOLVED",
                        loc.rel,
                        pair[0],
                        f"{pair[0]} and {pair[1]} conflict; add a Resolution naming the "
                        f"deciding source, or a U record citing both",
                    )
                )
    return out
