"""Source-ledger checks (IMPLEMENTATION_PLAN.md §10.2–§10.4)."""

from __future__ import annotations

from pflib import taxonomy, urls
from pflib.validators import Context, Finding, Loc, finding, record_check, workspace_check


@record_check("S")
def source_fields(ctx: Context, loc: Loc) -> list[Finding]:
    rec, out = loc.record, []
    tier_text = rec.get("Tier").strip()
    tier = int(tier_text) if tier_text.isdigit() else None
    if tier not in taxonomy.TIERS:
        out.append(finding("BAD_TIER", loc.rel, rec.id, f"{rec.id}: Tier {tier_text!r} is not 1–5"))
        tier = None
    category = rec.get("Category").strip()
    default = taxonomy.default_tier(category)
    if default is None:
        out.append(
            finding(
                "BAD_CATEGORY",
                loc.rel,
                rec.id,
                f"{rec.id}: Category {category!r} is not in the source taxonomy",
            )
        )
    elif tier is not None and tier < default:
        out.append(
            finding(
                "TIER_RAISED",
                loc.rel,
                rec.id,
                f"{rec.id}: Tier {tier} is better than the {category} default "
                f"({default}); tiers may only be lowered",
            )
        )
    authority = rec.get("Authority").strip()
    if authority not in taxonomy.AUTHORITIES:
        out.append(
            finding(
                "BAD_AUTHORITY",
                loc.rel,
                rec.id,
                f"{rec.id}: Authority {authority!r} is not High, Medium or Low",
            )
        )
    url, canonical = rec.get("URL").strip(), rec.get("Canonical URL").strip()
    if url and canonical and urls.canonicalize(url) != canonical:
        out.append(
            finding(
                "CANONICAL_URL_MISMATCH",
                loc.rel,
                rec.id,
                f"{rec.id}: Canonical URL should be {urls.canonicalize(url)}",
            )
        )
    return out


@workspace_check
def duplicate_sources(ctx: Context) -> list[Finding]:
    seen: dict[str, str] = {}
    out = []
    for loc in ctx.records("S"):
        key = loc.record.get("Canonical URL").strip()
        if not key:
            continue
        if key in seen:
            out.append(
                finding(
                    "DUPLICATE_SOURCE",
                    loc.rel,
                    loc.record.id,
                    f"{loc.record.id} has the same canonical URL as {seen[key]}",
                )
            )
        else:
            seen[key] = loc.record.id
    return out
