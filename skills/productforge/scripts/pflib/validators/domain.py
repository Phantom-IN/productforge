"""Domain-model checks: relationships and deletion semantics."""

from __future__ import annotations

from pflib import domain, ids, records
from pflib.validators import Context, Finding, Loc, finding, record_check, workspace_check


@record_check("E")
def relationships(ctx: Context, loc: Loc) -> list[Finding]:
    rec = loc.record
    out: list[Finding] = []
    _, bad = domain.parse_relationships(rec.get("Relationships"))
    for part in bad:
        out.append(finding("BAD_RELATIONSHIP", loc.rel, rec.id,
                           f"{rec.id}: relationship {part!r} should read "
                           "'E-NN (<1:1|1:N|N:1|N:M>, <required|optional>) [note]'"))  # fmt: skip
    if (
        rec.get("Deletion semantics").strip()
        and domain.deletion_kind(rec.get("Deletion semantics")) is None
    ):
        out.append(finding("BAD_DELETION_SEMANTICS", loc.rel, rec.id,
                           f"{rec.id}: deletion semantics should start with one of "
                           f"{', '.join(domain.DELETION_KINDS)}"))  # fmt: skip
    return out


@record_check("E")
def ui_state(ctx: Context, loc: Loc) -> list[Finding]:
    word = domain.looks_like_ui_state(loc.record) if records.is_active(loc.record) else None
    if word is None:
        return []
    msg = (f"{loc.record.id} {loc.record.title!r} looks like UI state ({word}), not an entity; "
           "model it as a field or setting of the entity that owns it")  # fmt: skip
    return [finding("ENTITY_LOOKS_LIKE_UI_STATE", loc.rel, loc.record.id, msg)]


@workspace_check
def inverse_relationships(ctx: Context) -> list[Finding]:
    ents = {loc.record.id: loc for loc in ctx.records("E") if records.is_active(loc.record)}
    links = {eid: domain.parse_relationships(loc.record.get("Relationships"))[0]
             for eid, loc in ents.items()}  # fmt: skip
    out: list[Finding] = []
    for eid, rels in sorted(links.items()):
        for rel in rels:
            if ids.is_provisional(rel.target) or rel.target not in links or rel.target <= eid:
                continue  # each pair is checked once, from its lower ID
            back = [r.cardinality for r in links[rel.target] if r.target == eid]
            if back and domain.INVERSE[rel.cardinality] not in back:
                out.append(finding("RELATIONSHIP_INCONSISTENT", ents[eid].rel, eid,
                                   f"{eid} → {rel.target} is {rel.cardinality} but {rel.target} → "
                                   f"{eid} is {', '.join(back)} (expected "
                                   f"{domain.INVERSE[rel.cardinality]})"))  # fmt: skip
    return out
