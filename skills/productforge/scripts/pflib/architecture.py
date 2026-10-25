"""Our architecture: shared analysis for validators, gates and views.

``spec/ARCHITECTURE.md`` describes **our** system. Its prose sections are written by the
systems-architect; this module reads the structured parts:

- ``## Stack`` — a table ``| Concern | Choice | ADR |`` with no TBD/unknown choices
- ``## External services`` — ``| Capability | Vendor | ADR | Test stand-in |`` (each vendor has a
  ``Topic: vendor`` ADR), ``## Toolchain`` — ``| Concern | Choice | Version | Verified |`` and
  ``## Environments`` — ``| Name | Secret | Used by | Development value |`` plus
  ``### Local services``
- ``## Components`` — ``- <name>: <role> (R-/A-/ADR- IDs)`` lines, each justified by an ID
- ``## Repository structure`` — a fenced tree (``pflib/repotree.py``)
- ``## Not applicable topics`` — ``- <topic>: <reason>`` for mandatory topics without an ADR
- ``## Convention-covered requirements`` — ``- R-NNN: <how>`` for requirements no ADR names
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pflib import catalog, records, repotree
from pflib.index import WorkspaceIndex

VERIFIED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\s+\S.*$")
UNPINNED_RE = re.compile(r"^\s*(latest|\*|x|n/?a)\s*$", re.I)
PORT_RE = re.compile(r"[,\s]\s*(?:port\s+)?\d{2,5}\s*$", re.I)
MANDATORY_TOPICS = ("identity", "tenancy", "authn", "authz", "storage", "realtime", "async",
                    "search", "files", "deployment")  # fmt: skip
TOPICS = (*MANDATORY_TOPICS, "vendor", "other")
ENFORCEMENT = ("test", "middleware", "db-constraint", "lint", "review")
DISCLAIMER = "This is our architecture, not a claim about"
INCOMPLETE_RE = re.compile(r"^\s*(|tbd|\?|unknown|todo|—|-)\s*$", re.I)
JUSTIFY_RE = re.compile(r"\b(?:R|A|ADR)-\d+\b")


def text_of(ws: Path) -> str | None:
    path = ws / catalog.ARCHITECTURE_PATH
    return path.read_text(encoding="utf-8") if path.is_file() else None


def section(text: str, title: str) -> str:
    return records.parse_document(text).section_text(title) or ""


def bullets(body: str) -> dict[str, str]:
    """``- key: value`` lines → {key: value} (keys lower-cased for topics, IDs kept)."""
    out: dict[str, str] = {}
    for line in body.splitlines():
        if line.startswith("- ") and ":" in line:
            key, _, value = line[2:].partition(":")
            out[key.strip()] = value.strip()
    return out


def table_rows(body: str) -> list[list[str]]:
    """Data rows (header and separator dropped) of the first pipe table in ``body``."""
    rows = []
    for line in body.splitlines():
        if line.startswith("|") and not re.match(r"^\|\s*:?-{3}", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append(cells)
    return rows[1:] if rows else []  # drop the header row


def stack_rows(text: str) -> list[list[str]]:
    return table_rows(section(text, "Stack"))


def external_service_rows(text: str) -> list[list[str]]:
    return table_rows(section(text, "External services"))


def toolchain_rows(text: str) -> list[list[str]]:
    return table_rows(section(text, "Toolchain"))


def environment_rows(text: str) -> list[list[str]]:
    return table_rows(section(text, "Environments").split("### Local services", 1)[0])


def local_services(text: str) -> list[str]:
    """``- <service>: <image>, <port>`` lines under ``### Local services``."""
    body = section(text, "Environments").partition("### Local services")[2]
    return [ln[2:].strip() for ln in body.splitlines() if ln.startswith("- ") and ln[2:].strip()]


def enforcement_kind(value: str) -> str | None:
    head = value.strip().lower()
    return next((k for k in ENFORCEMENT if re.match(rf"{re.escape(k)}\b", head)), None)


def alternatives(value: str) -> list[str]:
    return [a.strip() for a in value.split(";") if a.strip()]


def tree(text: str) -> tuple[set[str], str | None]:
    """(paths, error) for the repository structure section."""
    block = repotree.fenced_block(section(text, "Repository structure"))
    if block is None:
        return set(), "no fenced tree under ## Repository structure"
    try:
        paths = repotree.parse(block)
    except repotree.TreeError as exc:
        return set(), str(exc)
    if len(paths) < 2:
        return paths, "the tree declares fewer than two paths"
    return paths, None


@dataclass
class Coverage:
    unaddressed: list[str] = field(default_factory=list)  # R IDs
    unproposed: list[str] = field(default_factory=list)  # A IDs with no proposal
    multi_proposed: list[str] = field(default_factory=list)  # A IDs with several proposals
    topics_missing: list[str] = field(default_factory=list)
    by_requirement: dict[str, list[str]] = field(default_factory=dict)  # R → ADRs / "convention"
    deviations: dict[str, list[str]] = field(default_factory=dict)  # R → ADRs that deviate


def coverage(ws: Path, index: WorkspaceIndex | None = None) -> Coverage:
    index = index or WorkspaceIndex(ws)
    text = text_of(ws) or ""
    adrs = [a for _, a in index.records("ADR") if records.is_active(a)]
    conventions = bullets(section(text, "Convention-covered requirements"))
    out = Coverage()
    for _, r in index.records("R"):
        if not records.is_active(r):
            continue
        by = [a.id for a in adrs if r.id in records.parse_refs(a.get("Satisfies"))]
        if r.id in conventions:
            by.append("convention")
        out.by_requirement[r.id] = by
        dev = [a.id for a in adrs if r.id in records.parse_refs(a.get("Deviates from"))]
        if dev:
            out.deviations[r.id] = dev
        if not by:
            out.unaddressed.append(r.id)
    proposals: dict[str, int] = {}
    for _, ap in index.records("AP"):
        if records.is_active(ap):
            for ref in records.parse_refs(ap.get("Inference")):
                proposals[ref] = proposals.get(ref, 0) + 1
    for _, a in index.records("A"):
        if records.is_active(a):
            n = proposals.get(a.id, 0)
            if n == 0:
                out.unproposed.append(a.id)
            elif n > 1:
                out.multi_proposed.append(a.id)
    covered = {a.get("Topic").strip() for a in adrs} | {
        k.lower() for k in bullets(section(text, "Not applicable topics"))
    }
    out.topics_missing = [t for t in MANDATORY_TOPICS if t not in covered]
    return out
