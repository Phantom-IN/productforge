from __future__ import annotations

import pytest

from pflib import ids
from pflib.errors import UsageError


def test_padding_per_prefix() -> None:
    assert ids.format_id("S", 1) == "S-001"
    assert ids.format_id("RL", 1) == "RL-01"
    assert ids.format_id("ADR", 4) == "ADR-004"
    assert ids.format_id("E", 100) == "E-100"  # outgrows the minimum width


def test_allocate_from_max_and_never_fills_gaps() -> None:
    existing = ["D-001", "D-002", "D-007", "S-099", "D-?3"]
    assert ids.allocate("D", 2, existing) == ["D-008", "D-009"]
    assert ids.allocate("S", 1, existing) == ["S-100"]
    assert ids.allocate("U", 1, existing) == ["U-001"]


def test_allocate_respects_high_water_floor() -> None:
    assert ids.allocate("D", 1, ["D-002"], floor=10) == ["D-011"]
    assert ids.allocate("D", 1, ["D-020"], floor=10) == ["D-021"]


def test_provisional_detection_and_parse() -> None:
    assert ids.is_provisional("D-?7")
    assert not ids.is_provisional("D-007")
    assert not ids.is_provisional("nonsense")
    assert ids.parse("PS-?2") == ids.ParsedId("PS", 2, True)
    assert ids.provisional("F", 3) == "F-?3"


def test_unknown_prefix() -> None:
    with pytest.raises(UsageError) as info:
        ids.format_id("ZZ", 1)
    assert info.value.code == "UNKNOWN_PREFIX"
    assert ids.parse("ZZ-001", strict=False) is None
    with pytest.raises(UsageError):
        ids.parse("ZZ-001")


def test_max_id_ignores_other_prefixes_and_provisional() -> None:
    assert ids.max_id("D", ["DD-009", "D-?9", "D-004"]) == 4
