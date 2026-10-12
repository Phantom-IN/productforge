"""Reference fields that may only point at certain record types."""

from __future__ import annotations

from pflib import ids, records
from pflib.validators import Context, Finding, Loc, finding, record_check

# (prefix, field) → allowed prefixes of the referenced records
REF_TYPES: dict[tuple[str, str], tuple[str, ...]] = {
    ("D", "Evidence"): ("S",),
    ("D", "Related unknown"): ("U",),
    ("PS", "Evidence"): ("S", "D"),
    ("PS", "Unanswered questions"): ("U",),
    ("U", "Available evidence"): ("S", "D", "PS"),
    ("F", "Parent"): ("F",),
    ("F", "Surface"): ("PS",),
    ("F", "Evidence"): ("S", "D"),
    ("W", "Features"): ("F",),
    ("W", "Surfaces"): ("PS",),
    ("W", "Evidence"): ("S", "D"),
}


@record_check()
def reference_types(ctx: Context, loc: Loc) -> list[Finding]:
    assert loc.schema is not None
    out: list[Finding] = []
    for (prefix, key), allowed in REF_TYPES.items():
        if loc.schema.prefix != prefix:
            continue
        for ref in records.parse_refs(loc.record.get(key)):
            parsed = ids.parse(ref, strict=False)
            if parsed is not None and parsed.prefix not in allowed:
                out.append(
                    finding(
                        "WRONG_REF_TYPE",
                        loc.rel,
                        loc.record.id,
                        f"{loc.record.id}.{key} cites {ref}; only {'/'.join(allowed)} "
                        f"records belong there",
                    )  # fmt: skip
                )
    return out
