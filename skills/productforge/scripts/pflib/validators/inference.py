"""Architecture-inference checks (IMPLEMENTATION_PLAN.md §12.7, §18.5): no architecture
hallucination. A record describes the target's *behaviour*; its internals stay ``UNKNOWN`` unless a
CONFIRMED claim backed by a Tier ≤ 2 source states them."""

from __future__ import annotations

import re

from pflib import records, tech_terms
from pflib.validators import Context, Finding, Loc, finding, record_check
from pflib.validators.confidence_checks import source_index

MEASURABLE_RE = re.compile(
    r"\d|\b(must|never|always|at most|at least|within|every|no more than|no later than)\b", re.I
)


def is_unknown(value: str) -> bool:
    return value.strip().upper().startswith("UNKNOWN")


def qualifying_claims(ctx: Context, rec: records.Record) -> list[str]:
    """Cited D claims that are CONFIRMED and rest on a Tier ≤ 2 source."""
    index = source_index(ctx)
    out: list[str] = []
    for ref in records.parse_refs(rec.get("Evidence")):
        loc = ctx.get(ref)
        if loc is None or not ref.startswith("D-") or not records.is_active(loc.record):
            continue
        if loc.record.get("Confidence").strip().upper() != "CONFIRMED":
            continue
        tiers = [s.tier for s in index.effective_sources_of(ref) if s.tier is not None]
        if tiers and min(tiers) <= 2:
            out.append(ref)
    return out


def evidence_text(ctx: Context, rec: records.Record) -> str:
    """Text of the cited claims and sources (and the sources behind cited claims)."""
    parts: list[str] = []
    stack = list(records.parse_refs(rec.get("Evidence")))
    seen: set[str] = set()
    while stack:
        ref = stack.pop()
        loc = ctx.get(ref)
        if ref in seen or loc is None:
            continue
        seen.add(ref)
        parts.append(loc.record.title)
        parts.extend(loc.record.get(k) for k in ("Claim", "Engineering impact", "Notes"))
        if ref.startswith("D-"):
            stack.extend(records.parse_refs(loc.record.get("Evidence")))
    return "\n".join(parts)


@record_check("A")
def no_architecture_hallucination(ctx: Context, loc: Loc) -> list[Finding]:
    rec = loc.record
    if not records.is_active(rec):
        return []
    out: list[Finding] = []
    target = rec.get("Target implementation")
    qualified = qualifying_claims(ctx, rec)
    if target.strip() and not is_unknown(target) and not qualified:
        msg = (f"{rec.id}: Target implementation {target.strip()!r} needs a CONFIRMED claim with "
               "Tier ≤ 2 evidence in Evidence; otherwise write UNKNOWN")  # fmt: skip
        out.append(finding("TARGET_IMPL_UNSUPPORTED", loc.rel, rec.id, msg))
    requirement = rec.get("Our requirement")
    if requirement.strip() and not MEASURABLE_RE.search(requirement):
        out.append(finding("REQUIREMENT_NOT_MEASURABLE", loc.rel, rec.id,
                           f"{rec.id}: state 'Our requirement' measurably (a number and unit, or "
                           "must/never/within …)"))  # fmt: skip
    stated = set(tech_terms.find(evidence_text(ctx, rec)))
    for key in ("Observation", "Engineering implication"):
        terms = [t for t in tech_terms.find(rec.get(key)) if t not in stated]
        if terms:
            out.append(finding("TECH_ASSERTION_IN_OBSERVATION", loc.rel, rec.id,
                               f"{rec.id}.{key} names {', '.join(terms)}, which no cited claim or "
                               "source states; describe behaviour, not technology"))  # fmt: skip
    return out
