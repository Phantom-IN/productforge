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
    ("E", "Relationships"): ("E",),
    ("E", "Features"): ("F",),
    ("E", "Evidence"): ("S", "D"),
    ("E", "Related unknown"): ("U",),
    ("RL", "Inherits"): ("RL",),
    ("RL", "Evidence"): ("S", "D"),
    ("PR", "Resource"): ("E",),
    ("PR", "Grants"): ("RL",),
    ("PR", "Evidence"): ("S", "D"),
    ("PR", "Related unknown"): ("U",),
    ("I", "Evidence"): ("S", "D"),
    ("I", "Related unknown"): ("U",),
    ("A", "Evidence"): ("S", "D"),
    ("A", "Derived from"): ("W", "D", "F", "E", "I", "PR"),
    ("A", "Related unknown"): ("U",),
    ("C", "Table-stakes features"): ("F",),
    ("C", "Common complaints"): ("S",),
    ("C", "Evidence"): ("S", "D"),
    ("FS", "Competitors"): ("C",),
    ("FS", "Evidence"): ("S", "D"),
    ("SC", "Feature"): ("F",),
    ("R", "Derived from"): ("F", "W", "A", "D", "U", "E", "I", "PR"),
    ("R", "Features"): ("F",),
    ("UD", "Unknown"): ("U",),
    ("ADR", "Satisfies"): ("R", "A"),
    ("INV", "Derived from"): ("R", "ADR", "E", "PR", "A"),
    ("AP", "Inference"): ("A",),
    ("AP", "Decision"): ("ADR",),
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
