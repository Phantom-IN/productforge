"""Schema, reference, status, identity and quote checks for every record artifact."""

from __future__ import annotations

import difflib
import re
from itertools import combinations

from pflib import catalog, ids, records
from pflib.records import Document
from pflib.validators import (
    Context,
    Finding,
    Loc,
    artifact_check,
    finding,
    record_check,
    workspace_check,
)

# Allowed on any record: the amendable fields (Status, Reason — required with Status: rejected —
# and Resolution), so every record type can be superseded, rejected or marked conflicting.
GENERIC_OPTIONAL = ("Status", "Reason", "Resolution")
STATUS_GENERIC = ("active", "rejected")
STATUS_ADR = ("accepted", "global")
NEAR_DUP_RATIO = 0.92
QUOTE_RE = re.compile(r"[\"“]([^\"“”\n]+)[\"”]")
FENCE_RE = re.compile(r"^(?:```|~~~)")


@record_check()
def schema_fields(ctx: Context, loc: Loc) -> list[Finding]:
    assert loc.schema is not None
    rec, out = loc.record, []
    for key in loc.schema.required:
        if key not in rec.fields:
            out.append(finding("MISSING_FIELD", loc.rel, rec.id, f"{rec.id} is missing {key!r}"))
        elif not rec.fields[key].strip() and key not in loc.schema.allow_empty:
            out.append(finding("EMPTY_FIELD", loc.rel, rec.id, f"{rec.id} has an empty {key!r}"))
    allowed = set(loc.schema.fields) | set(GENERIC_OPTIONAL)
    allowed |= set(catalog.RESERVED_FIELDS.get(loc.schema.prefix, ((), ""))[0])  # features.py
    for key in rec.order:
        if key not in allowed:
            out.append(
                finding("UNKNOWN_FIELD", loc.rel, rec.id, f"{rec.id}: {key!r} is not in the schema")
            )
    return out


@record_check()
def identity_and_refs(ctx: Context, loc: Loc) -> list[Finding]:
    assert loc.schema is not None
    rec, out = loc.record, []
    provisional = [rec.id] if ids.is_provisional(rec.id) else []
    for value in rec.fields.values():
        provisional += [r for r in records.parse_refs(value) if ids.is_provisional(r)]
    if provisional:
        listed = ", ".join(dict.fromkeys(provisional))
        out.append(
            finding(
                "PROVISIONAL_ID_IN_CANONICAL",
                loc.rel,
                rec.id,
                f"{rec.id}: provisional IDs in a canonical file ({listed}); merge staging instead",
            )
        )
    for key in loc.schema.ref_fields:
        for ref in records.parse_refs(rec.get(key)):
            if not ids.is_provisional(ref) and ctx.get(ref) is None:
                out.append(
                    finding("DANGLING_REF", loc.rel, rec.id, f"{rec.id}.{key} cites missing {ref}")
                )
    return out


@record_check()
def status_values(ctx: Context, loc: Loc) -> list[Finding]:
    rec = loc.record
    if "Status" not in rec.fields:
        return []
    status = rec.get("Status").strip()
    is_adr = loc.schema is not None and loc.schema.prefix == "ADR"
    simple = STATUS_ADR if is_adr else STATUS_GENERIC
    out: list[Finding] = []
    if status in simple:
        if status == "rejected" and not rec.get("Reason").strip():
            out.append(
                finding("BAD_STATUS", loc.rel, rec.id, f"{rec.id} is rejected without a Reason")
            )
        return out
    if status.startswith("superseded-by "):
        targets = records.parse_refs(status)
        own = ids.parse(rec.id, strict=False)
        if len(targets) != 1:
            return [finding("BAD_STATUS", loc.rel, rec.id, f"{rec.id}: superseded-by needs one ID")]
        target = targets[0]
        tparsed = ids.parse(target, strict=False)
        if target == rec.id:
            out.append(finding("SUPERSEDED_TARGET_MISSING", loc.rel, rec.id,
                               f"{rec.id} is superseded by itself"))  # fmt: skip
        elif ctx.get(target) is None or not own or not tparsed or tparsed.prefix != own.prefix:
            out.append(
                finding(
                    "SUPERSEDED_TARGET_MISSING",
                    loc.rel,
                    rec.id,
                    f"{rec.id} is superseded by {target}, which does not exist as a "
                    f"{own.prefix if own else '?'} record",
                )
            )
        return out
    if status.startswith("conflicting-with ") and not is_adr:
        for ref in records.parse_refs(status):
            if ctx.get(ref) is None:
                out.append(
                    finding("DANGLING_REF", loc.rel, rec.id, f"{rec.id}.Status cites missing {ref}")
                )
        if records.parse_refs(status):
            return out
    allowed = " | ".join(
        [*simple, "superseded-by <ID>"] + ([] if is_adr else ["conflicting-with <ID>"])
    )
    return [
        finding(
            "BAD_STATUS", loc.rel, rec.id, f"{rec.id}: Status {status!r} is not one of {allowed}"
        )
    ]


@workspace_check
def duplicate_ids(ctx: Context) -> list[Finding]:
    out = []
    for record_id, locs in sorted(ctx.by_id.items()):
        if len(locs) > 1:
            where = ", ".join(loc.rel for loc in locs)
            out.append(
                finding(
                    "DUPLICATE_ID", locs[1].rel, record_id, f"{record_id} is defined in {where}"
                )
            )
    return out


@workspace_check
def misplaced_records(ctx: Context) -> list[Finding]:
    return [
        finding(
            "UNKNOWN_PREFIX",
            loc.rel,
            loc.record.id,
            f"{loc.record.id}: {loc.record.prefix} records do not belong in {loc.spec.path}",
        )
        for locs in ctx.by_id.values()
        for loc in locs
        if loc.schema is None
    ]


# Titles written by scripts from distinct keys (observe ingest): never near-duplicates.
GENERATED_TITLES = frozenset({"OB"})


@workspace_check
def near_duplicate_titles(ctx: Context) -> list[Finding]:
    out: list[Finding] = []
    by_prefix: dict[str, list[Loc]] = {}
    for loc in ctx.records():
        if loc.schema is not None and records.is_active(loc.record):  # superseded = resolved
            if loc.schema.prefix in GENERATED_TITLES:
                continue
            by_prefix.setdefault(loc.schema.prefix, []).append(loc)
    for locs in by_prefix.values():
        normed = [(loc, records.normalise_text(loc.record.title)) for loc in locs]
        for (a, na), (b, nb) in combinations(normed, 2):
            if re.findall(r"\d+", a.record.title) != re.findall(r"\d+", b.record.title):
                continue  # "v3.2" vs "v3.4", "Tier 1" vs "Tier 2": different things by number
            if re.findall(r"`[^`]+`", a.record.title) != re.findall(r"`[^`]+`", b.record.title):
                continue  # "`GET /tasks`" vs "`GET /tasks/:id`": different routes or endpoints
            if na and nb and difflib.SequenceMatcher(None, na, nb).ratio() >= NEAR_DUP_RATIO:
                out.append(
                    finding(
                        "NEAR_DUPLICATE_TITLE",
                        b.rel,
                        b.record.id,
                        f"{b.record.id} {b.record.title!r} looks like {a.record.id} "
                        f"{a.record.title!r}; merge them if they state the same fact",
                    )
                )
    return out


@artifact_check
def long_quotes(ctx: Context, rel: str, spec: object, doc: Document) -> list[Finding]:
    out: list[Finding] = []
    in_fence = False
    for i, raw in enumerate(doc.lines):
        line = raw.rstrip("\r\n")
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in QUOTE_RE.finditer(line):
            words = len(m.group(1).split())
            if words > ctx.max_quote_words:
                rec = next((r for r in doc.records if r.start <= i < r.end), None)
                out.append(
                    finding(
                        "QUOTE_TOO_LONG",
                        rel,
                        rec.id if rec else None,
                        f"{rel}:{i + 1}: quote of {words} words exceeds quotes.max_words="
                        f"{ctx.max_quote_words}; paraphrase and cite the source instead",
                    )
                )
    return out
