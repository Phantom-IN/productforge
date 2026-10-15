"""Feature-matrix checks and enum checks for every schema."""

from __future__ import annotations

from pflib import catalog, records
from pflib.validators import Context, Finding, Loc, finding, record_check, workspace_check


@record_check()
def enums(ctx: Context, loc: Loc) -> list[Finding]:
    assert loc.schema is not None
    out: list[Finding] = []
    for (prefix, key), allowed in catalog.ENUMS.items():
        if prefix != loc.schema.prefix or key not in loc.record.fields:
            continue
        value = loc.record.get(key).strip()
        if value and value not in allowed:
            out.append(finding("BAD_ENUM", loc.rel, loc.record.id,
                               f"{loc.record.id}.{key} is {value!r}; use one of "
                               f"{', '.join(allowed)}"))  # fmt: skip
    return out


@record_check()
def reserved_fields(ctx: Context, loc: Loc) -> list[Finding]:
    assert loc.schema is not None
    fields, why = catalog.RESERVED_FIELDS.get(loc.schema.prefix, ((), ""))
    found = [k for k in loc.record.order if k in fields]
    if not found:
        return []
    return [finding("FIELD_NOT_YET_ALLOWED", loc.rel, loc.record.id,
                    f"{loc.record.id} carries {', '.join(found)}: {why}")]  # fmt: skip


def _parent(rec: records.Record) -> str | None:
    return next(iter(records.parse_refs(rec.get("Parent"))), None)


@workspace_check
def feature_tree(ctx: Context) -> list[Finding]:
    feats = {loc.record.id: loc for loc in ctx.records("F")}
    out: list[Finding] = []
    for fid, loc in feats.items():
        parent_id = _parent(loc.record)
        if parent_id and parent_id in feats:
            mine = loc.record.get("Domain").strip()
            theirs = feats[parent_id].record.get("Domain").strip()
            if mine != theirs:
                out.append(finding("PARENT_DOMAIN_MISMATCH", loc.rel, fid,
                                   f"{fid} is in {mine!r} but its parent {parent_id} is in "
                                   f"{theirs!r}"))  # fmt: skip
        seen = [fid]
        current = parent_id
        while current and current in feats:
            if current in seen:
                cycle = " → ".join([*seen[seen.index(current) :], current])
                if min(seen[seen.index(current) :]) == fid:  # report each cycle once
                    out.append(finding("PARENT_CYCLE", loc.rel, fid, f"parent cycle: {cycle}"))
                break
            seen.append(current)
            current = _parent(feats[current].record)
    return out
