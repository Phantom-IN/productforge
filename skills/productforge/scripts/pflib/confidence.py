"""Mechanical confidence rules (IMPLEMENTATION_PLAN.md §11). Pure, no I/O.

| Confidence | Requirement on the record's evidence                                         |
|------------|------------------------------------------------------------------------------|
| CONFIRMED  | ≥1 source with Tier ≤ 2                                                       |
| PROBABLE   | ≥2 sources on distinct registrable domains with Tier ≤ 4, or ≥1 with Tier ≤ 3 |
| INFERRED   | ``Derived from`` cites ≥1 observation record (anything but S or U)            |
| UNKNOWN    | ``Related unknown`` cites a U record                                          |

A record's evidence is resolved *transitively*: ``Evidence`` may cite sources directly or
other records (e.g. a feature citing claims), whose own ``Evidence`` is followed down to the
sources. Tier-5-only evidence can never support more than INFERRED (implied by the table).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from pflib import ids, records
from pflib.records import Record

STATES = ("CONFIRMED", "PROBABLE", "INFERRED", "UNKNOWN")
NON_OBSERVATION_PREFIXES = ("S", "U")
PROVIDER_REPORT = "provider-report"


@dataclass(frozen=True)
class SourceInfo:
    id: str
    tier: int | None  # None when the source's Tier is malformed
    domain: str
    category: str = ""


@dataclass
class SourceIndex:
    """Sources by ID plus each record's ``Evidence`` references (for transitive lookups)."""

    sources: dict[str, SourceInfo] = field(default_factory=dict)
    evidence: dict[str, list[str]] = field(default_factory=dict)

    def effective_sources(self, rec: Record) -> list[SourceInfo]:
        found: dict[str, SourceInfo] = {}
        seen: set[str] = {rec.id}
        stack = list(records.parse_refs(rec.get("Evidence")))
        while stack:
            ref = stack.pop()
            if ref in seen:
                continue
            seen.add(ref)
            if ref in self.sources:
                found[ref] = self.sources[ref]
            else:
                stack.extend(self.evidence.get(ref, []))
        return sorted(found.values(), key=lambda s: s.id)


@dataclass(frozen=True)
class Violation:
    code: str  # BAD_CONFIDENCE | CONFIDENCE_RULE | PROVIDER_REPORT_AS_EVIDENCE
    message: str


def _tiers(srcs: list[SourceInfo]) -> list[int]:
    return sorted(s.tier for s in srcs if s.tier is not None)


def check_record(rec: Record, index: SourceIndex) -> list[Violation]:
    """Violations of the §11 rules for one record (empty when it has no Confidence)."""
    if "Confidence" not in rec.fields:
        return []
    value = rec.get("Confidence").strip()
    if value not in STATES:
        return [
            Violation("BAD_CONFIDENCE", f"Confidence {value!r} is not one of {', '.join(STATES)}")
        ]
    srcs = index.effective_sources(rec)
    tiers = _tiers(srcs)
    best = f"best evidence: Tier {tiers[0]}" if tiers else "no resolvable source evidence"
    only_tier5 = bool(tiers) and min(tiers) == 5
    cap = " (Tier-5-only evidence caps at INFERRED)" if only_tier5 else ""
    if (
        value in ("CONFIRMED", "PROBABLE")
        and srcs
        and all(s.category == PROVIDER_REPORT for s in srcs)
    ):
        return [
            Violation(
                "PROVIDER_REPORT_AS_EVIDENCE",
                f"{value} rests only on a delegated skill's report; cite the original URLs it "
                "names as sources (a report alone caps at INFERRED)",
            )
        ]
    if value == "CONFIRMED" and not any(t <= 2 for t in tiers):
        return [Violation("CONFIDENCE_RULE", f"CONFIRMED needs a Tier ≤ 2 source; {best}{cap}")]
    if value == "PROBABLE":
        domains = {s.domain for s in srcs if s.tier is not None and s.tier <= 4}
        if not (len(domains) >= 2 or any(t <= 3 for t in tiers)):
            return [
                Violation(
                    "CONFIDENCE_RULE",
                    "PROBABLE needs ≥2 Tier ≤ 4 sources on distinct sites or one Tier ≤ 3 "
                    f"source; {best}, distinct sites: {len(domains)}{cap}",
                )
            ]
    if value == "INFERRED":
        derived = [
            r
            for r in records.parse_refs(rec.get("Derived from"))
            if (p := ids.parse(r, strict=False)) and p.prefix not in NON_OBSERVATION_PREFIXES
        ]
        if not derived:
            return [
                Violation(
                    "CONFIDENCE_RULE",
                    "INFERRED needs 'Derived from' citing at least one observation record "
                    "(a claim, feature, workflow, inference, …)",
                )
            ]
    if value == "UNKNOWN":
        unknowns = [r for r in records.parse_refs(rec.get("Related unknown")) if r.startswith("U-")]
        if not unknowns:
            return [
                Violation("CONFIDENCE_RULE", "UNKNOWN needs 'Related unknown' citing a U record")
            ]
    return []


def conflict_partners(rec: Record) -> list[str]:
    """IDs this record declares a conflict with (Status ``conflicting-with`` and ``Conflicts``)."""
    partners: list[str] = []
    status = rec.get("Status").strip()
    if status.startswith("conflicting-with"):
        partners.extend(records.parse_refs(status))
    partners.extend(records.parse_refs(rec.get("Conflicts")))
    return list(dict.fromkeys(partners))


def build_index(
    all_records: list[Record],
    tier_of: Callable[[Record], int | None],
    domain_of: Callable[[Record], str],
    category_of: Callable[[Record], str] = lambda rec: rec.get("Category").strip(),
) -> SourceIndex:
    index = SourceIndex()
    for rec in all_records:
        parsed = ids.parse(rec.id, strict=False)
        if parsed is None:
            continue
        if parsed.prefix == "S":
            index.sources[rec.id] = SourceInfo(
                rec.id, tier_of(rec), domain_of(rec), category_of(rec)
            )
        else:
            index.evidence[rec.id] = records.parse_refs(rec.get("Evidence"))
    return index


def parse_tier(value: str) -> int | None:
    try:
        tier = int(value.strip())
    except ValueError:
        return None
    return tier if 1 <= tier <= 5 else None
