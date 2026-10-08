from __future__ import annotations

import pytest

from pflib import confidence, records
from pflib.confidence import SourceIndex, SourceInfo


def rec(text: str) -> records.Record:
    return records.parse_document(text).records[0]


def claim(conf: str, evidence: str = "", **extra: str) -> records.Record:
    body = f"### D-900 — x\n- Claim: x\n- Evidence: {evidence}\n- Confidence: {conf}\n"
    body += "".join(f"- {k.replace('_', ' ').capitalize()}: {v}\n" for k, v in extra.items())
    return rec(body)


INDEX = SourceIndex(
    sources={
        "S-001": SourceInfo("S-001", 1, "tasklet.example"),
        "S-002": SourceInfo("S-002", 2, "tasklet.example"),
        "S-003": SourceInfo("S-003", 3, "reviews.example"),
        "S-004": SourceInfo("S-004", 4, "community.example"),
        "S-005": SourceInfo("S-005", 4, "social.example"),
        "S-006": SourceInfo("S-006", 4, "community.example"),
        "S-007": SourceInfo("S-007", 5, "rumors.example"),
        "S-008": SourceInfo("S-008", None, "broken.example"),
    },
    evidence={
        "D-001": ["S-001"],
        "D-002": ["S-004"],
        "F-001": ["D-001"],
        "D-010": ["D-011"],
        "D-011": ["D-010"],
    },
)


def codes(r: records.Record) -> list[str]:
    return [v.code for v in confidence.check_record(r, INDEX)]


@pytest.mark.parametrize(
    "conf, evidence, extra, ok",
    [
        ("CONFIRMED", "S-001", {}, True),
        ("CONFIRMED", "S-002", {}, True),
        ("CONFIRMED", "S-003", {}, False),
        ("CONFIRMED", "S-004, S-005", {}, False),
        ("CONFIRMED", "", {}, False),
        ("PROBABLE", "S-004, S-005", {}, True),  # two Tier-4 sources, distinct sites
        ("PROBABLE", "S-004, S-006", {}, False),  # two Tier-4 sources, same site
        ("PROBABLE", "S-003", {}, True),  # one Tier-3 source
        ("PROBABLE", "S-004", {}, False),
        ("PROBABLE", "S-007, S-004", {}, False),  # Tier 5 does not count towards distinct sites
        ("INFERRED", "", {"derived_from": "D-001"}, True),
        ("INFERRED", "S-001", {}, False),
        (
            "INFERRED",
            "",
            {"derived_from": "S-001, U-001"},
            False,
        ),  # sources/unknowns are not observations
        ("UNKNOWN", "S-007", {"related_unknown": "U-003"}, True),
        ("UNKNOWN", "S-007", {}, False),
        ("UNKNOWN", "", {"related_unknown": "D-001"}, False),
    ],
)
def test_rules(conf: str, evidence: str, extra: dict[str, str], ok: bool) -> None:
    assert codes(claim(conf, evidence, **extra)) == ([] if ok else ["CONFIDENCE_RULE"])


def test_tier5_only_evidence_caps_at_inferred() -> None:
    for conf in ("CONFIRMED", "PROBABLE"):
        (v,) = confidence.check_record(claim(conf, "S-007"), INDEX)
        assert v.code == "CONFIDENCE_RULE" and "caps at INFERRED" in v.message
    assert codes(claim("INFERRED", "S-007", derived_from="D-001")) == []


def test_evidence_resolves_transitively_through_records() -> None:
    feature = rec("### F-009 — y\n- Evidence: F-001\n- Confidence: CONFIRMED\n")
    assert codes(feature) == []  # F-001 → D-001 → S-001 (Tier 1)
    assert [s.id for s in INDEX.effective_sources(feature)] == ["S-001"]
    weak = rec("### F-010 — z\n- Evidence: D-002\n- Confidence: CONFIRMED\n")
    assert codes(weak) == ["CONFIDENCE_RULE"]


def test_cycles_and_malformed_tiers_are_safe() -> None:
    looping = rec("### F-011 — loop\n- Evidence: D-010\n- Confidence: PROBABLE\n")
    assert codes(looping) == ["CONFIDENCE_RULE"]
    assert codes(claim("CONFIRMED", "S-008")) == ["CONFIDENCE_RULE"]


def test_bad_confidence_and_records_without_confidence() -> None:
    assert codes(claim("SURE", "S-001")) == ["BAD_CONFIDENCE"]
    assert codes(claim("confirmed", "S-001")) == ["BAD_CONFIDENCE"]  # enum is case-sensitive
    assert codes(rec("### S-010 — a source\n- Tier: 1\n")) == []


def test_conflict_partners() -> None:
    r = rec("### D-1 — a\n- Status: conflicting-with D-002, D-003\n- Conflicts: D-004, D-002\n")
    assert confidence.conflict_partners(r) == ["D-002", "D-003", "D-004"]
    assert confidence.conflict_partners(rec("### D-1 — a\n- Status: active\n")) == []


def test_parse_tier() -> None:
    assert [confidence.parse_tier(v) for v in ("1", " 5 ", "0", "6", "two", "")] == [
        1,
        5,
        None,
        None,
        None,
        None,
    ]
