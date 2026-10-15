"""Permissions checks: complete cells, explained ? and Limited."""

from __future__ import annotations

from pflib import domain, records
from pflib.validators import Context, Finding, Loc, finding, record_check, workspace_check


def _active_roles(ctx: Context) -> list[str]:
    return sorted(loc.record.id for loc in ctx.records("RL") if records.is_active(loc.record))


@record_check("PR")
def grants(ctx: Context, loc: Loc) -> list[Finding]:
    rec = loc.record
    if not records.is_active(rec):
        return []
    cells, bad = domain.parse_grants(rec.get("Grants"))
    out = [finding("BAD_GRANT", loc.rel, rec.id,
                   f"{rec.id}: grant {part!r} should read 'RL-NN <✓|✗|Limited|?>'")
           for part in bad]  # fmt: skip
    missing = [rl for rl in _active_roles(ctx) if rl not in cells]
    if missing:
        out.append(finding("PERMISSION_CELL_MISSING", loc.rel, rec.id,
                           f"{rec.id} has no cell for {', '.join(missing)}"))  # fmt: skip
    values = set(cells.values())
    if "?" in values and not records.parse_refs(rec.get("Related unknown")):
        msg = f"{rec.id} has a '?' cell; cite the U record under 'Related unknown'"
        out.append(finding("UNKNOWN_CELL_NO_U", loc.rel, rec.id, msg))
    if "Limited" in values and not rec.get("Limited means").strip():
        msg = f"{rec.id} has a 'Limited' cell; say what is limited in 'Limited means'"
        out.append(finding("LIMITED_WITHOUT_MEANS", loc.rel, rec.id, msg))
    return out


@workspace_check
def one_rule_per_cell_row(ctx: Context) -> list[Finding]:
    seen: dict[tuple[str, str], str] = {}
    out: list[Finding] = []
    for loc in sorted(ctx.records("PR"), key=lambda loc: loc.record.id):
        rec = loc.record
        if not records.is_active(rec):
            continue
        key = (",".join(records.parse_refs(rec.get("Resource"))), rec.get("Action").strip().lower())
        if key in seen:
            out.append(finding("DUPLICATE_PERMISSION_RULE", loc.rel, rec.id,
                               f"{rec.id} repeats {seen[key]} ({key[0]} {key[1]}); supersede the "
                               "old rule with an amendment"))  # fmt: skip
        else:
            seen[key] = rec.id
    return out


@workspace_check
def entities_have_rules(ctx: Context) -> list[Finding]:
    features = {loc.record.id: loc.record for loc in ctx.records("F")}
    covered = {
        ref
        for loc in ctx.records("PR")
        if records.is_active(loc.record)
        for ref in records.parse_refs(loc.record.get("Resource"))
    }
    out: list[Finding] = []
    for loc in ctx.records("E"):
        e = loc.record
        if records.is_active(e) and e.id not in covered and domain.is_mutable(e, features):
            out.append(finding("ENTITY_WITHOUT_PERMISSIONS", loc.rel, e.id,
                               f"{e.id} {e.title} can be changed by users but no PR rule names "
                               "it as Resource"))  # fmt: skip
    return out
