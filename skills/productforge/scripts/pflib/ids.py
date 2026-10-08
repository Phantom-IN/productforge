"""Record identity (IMPLEMENTATION_PLAN.md §6.1).

Final IDs look like ``D-041`` (zero-padded to the prefix's minimum width; wider numbers
are allowed once a set outgrows it). Provisional IDs written by agents in staging look
like ``D-?7`` and are rewritten by ``pf.py merge``. IDs are never reused: allocation
continues from the highest ID ever seen (canonical files and ``.productforge/ids.json``).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, overload

from pflib.errors import UsageError

# prefix → minimum zero-padded width. Order mirrors the §6.1 table.
PREFIXES: dict[str, int] = {
    "S": 3,  # source
    "D": 3,  # discovery claim
    "U": 3,  # unknown
    "PS": 2,  # product surface
    "F": 3,  # feature
    "W": 3,  # workflow
    "E": 2,  # domain entity
    "RL": 2,  # role
    "PR": 3,  # permission rule
    "I": 2,  # integration
    "A": 3,  # architecture inference
    "AP": 3,  # architecture proposal
    "C": 2,  # competitor
    "FS": 3,  # competitor feature signal
    "SC": 3,  # feature score card
    "UD": 3,  # unknown's V1 default
    "R": 3,  # our requirement
    "INV": 2,  # invariant
    "ADR": 3,  # architecture decision
}

ANY_ID_RE = re.compile(r"(?<![A-Za-z0-9?-])[A-Z]{1,3}-(?:\?\d+|\d+)(?![0-9A-Za-z])")
_ID_RE = re.compile(r"^(?P<prefix>[A-Z]{1,3})-(?P<prov>\?)?(?P<num>\d+)$")
PROVISIONAL_RE = re.compile(
    r"(?<![A-Za-z0-9?-])(?P<prefix>[A-Z]{1,3})-\?(?P<num>\d+)(?![0-9A-Za-z])"
)


@dataclass(frozen=True)
class ParsedId:
    prefix: str
    number: int
    provisional: bool


@overload
def parse(value: str, strict: Literal[True] = ...) -> ParsedId: ...
@overload
def parse(value: str, strict: bool) -> ParsedId | None: ...


def parse(value: str, strict: bool = True) -> ParsedId | None:
    """Split an ID into prefix/number. Unknown prefixes → ``UsageError`` (or None)."""
    m = _ID_RE.match(value)
    if not m or m.group("prefix") not in PREFIXES:
        if strict:
            raise UsageError(f"not a valid record id: {value!r}", code="UNKNOWN_PREFIX")
        return None
    return ParsedId(m.group("prefix"), int(m.group("num")), m.group("prov") is not None)


def check_prefix(prefix: str) -> str:
    if prefix not in PREFIXES:
        known = ", ".join(PREFIXES)
        raise UsageError(
            f"unknown record prefix {prefix!r} (known: {known})", code="UNKNOWN_PREFIX"
        )
    return prefix


def format_id(prefix: str, number: int) -> str:
    return f"{check_prefix(prefix)}-{number:0{PREFIXES[prefix]}d}"


def provisional(prefix: str, number: int) -> str:
    return f"{check_prefix(prefix)}-?{number}"


def is_provisional(value: str) -> bool:
    parsed = parse(value, strict=False)
    return parsed is not None and parsed.provisional


def max_id(prefix: str, existing: Iterable[str]) -> int:
    """Highest final number for ``prefix`` among ``existing`` IDs (0 if none)."""
    best = 0
    for value in existing:
        parsed = parse(value, strict=False)
        if parsed and parsed.prefix == prefix and not parsed.provisional:
            best = max(best, parsed.number)
    return best


def allocate(prefix: str, n: int, existing: Iterable[str], floor: int = 0) -> list[str]:
    """Next ``n`` IDs after max(existing, floor). Gaps are never filled."""
    start = max(max_id(check_prefix(prefix), existing), floor) + 1
    return [format_id(prefix, start + k) for k in range(n)]
