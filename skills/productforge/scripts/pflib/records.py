"""Canonical Markdown record grammar (IMPLEMENTATION_PLAN.md §6.2).

A record is a level-3 heading followed by a key/value bullet list::

    ### D-041 — Issues may optionally belong to projects
    - Claim: Issues may optionally belong to projects.
    - Evidence: S-004, S-017
    - Engineering impact: issues.project_id must be nullable;
      continuation lines are indented two spaces.

Any ``###`` heading whose text starts with an ID-like token is parsed as a record and
must be well formed; other headings are prose. Headings inside fenced code blocks are
ignored. Matrices are GFM tables (conventionally under ``## Matrix``).

Well-formed (canonical) text round-trips byte-for-byte through
``parse_document`` → ``serialize_document``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pflib import ids
from pflib.errors import CheckFailed

RECORD_HEAD_RE = re.compile(r"^### (?P<id>[A-Z]{1,3}-(?:\?\d+|\d+)) — (?P<title>\S.*)$")
ID_LIKE_HEAD_RE = re.compile(r"^### [A-Z]{1,3}-[?\d]")
FIELD_RE = re.compile(r"^- (?P<key>[^\s:][^:\n]*?):(?: (?P<value>.*))?$")
HEADING_RE = re.compile(r"^(?P<hashes>#{1,6}) (?P<title>.*)$")
FENCE_RE = re.compile(r"^(?:```|~~~)")
TABLE_SEP_RE = re.compile(r"^\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?\s*$")
CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")


class RecordParseError(CheckFailed):
    code = "PARSE_ERROR"

    def __init__(self, message: str, line: int, path: str | None = None) -> None:
        where = f"{path}:{line}" if path else f"line {line}"
        super().__init__(f"{where}: {message}", details={"line": line, "path": path})
        self.line = line


@dataclass
class Record:
    id: str
    title: str
    fields: dict[str, str] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    start: int = 0  # first line index (heading), 0-based
    end: int = 0  # line index after the last field line
    section: str | None = None  # enclosing "## ..." heading text, if any

    @property
    def prefix(self) -> str:
        return ids.parse(self.id).prefix

    @property
    def raw_span(self) -> tuple[int, int]:
        return self.start, self.end

    def get(self, key: str, default: str = "") -> str:
        return self.fields.get(key, default)

    def set(self, key: str, value: str) -> None:
        if key not in self.fields:
            self.order.append(key)
        self.fields[key] = value


@dataclass
class Table:
    headers: list[str]
    rows: list[list[str]]
    start: int = 0
    end: int = 0
    section: str | None = None


@dataclass
class Section:
    title: str
    level: int
    start: int  # line index of the heading


@dataclass
class Document:
    text: str
    lines: list[str]  # with line endings
    records: list[Record] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    path: str | None = None

    def record(self, record_id: str) -> Record | None:
        return next((r for r in self.records if r.id == record_id), None)

    def section_text(self, title: str) -> str | None:
        """Body text (without the heading line) of the first section titled ``title``."""
        for i, sec in enumerate(self.sections):
            if sec.title == title:
                end = len(self.lines)
                for nxt in self.sections[i + 1 :]:
                    if nxt.level <= sec.level:
                        end = nxt.start
                        break
                return "".join(self.lines[sec.start + 1 : end])
        return None


def _strip_eol(line: str) -> str:
    return line.rstrip("\r\n")


def parse_document(text: str, path: str | None = None) -> Document:
    """Parse records, tables and section headings from ``text``.

    Raises ``RecordParseError`` (code ``PARSE_ERROR``) for malformed records.
    """
    lines = text.splitlines(keepends=True)
    doc = Document(text=text, lines=lines, path=path)
    in_fence = False
    current_section: str | None = None
    seen_ids: dict[str, int] = {}
    i = 0
    while i < len(lines):
        line = _strip_eol(lines[i])
        if FENCE_RE.match(line):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence:
            i += 1
            continue
        if ID_LIKE_HEAD_RE.match(line):
            rec, i = _parse_record(lines, i, path)
            if rec.id in seen_ids:
                raise RecordParseError(
                    f"duplicate record id {rec.id} (first defined on line {seen_ids[rec.id] + 1})",
                    rec.start + 1,
                    path,
                )
            seen_ids[rec.id] = rec.start
            rec.section = current_section
            doc.records.append(rec)
            continue
        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group("hashes"))
            doc.sections.append(Section(heading.group("title"), level, i))
            if level <= 2:
                current_section = heading.group("title") if level == 2 else None
            i += 1
            continue
        if (
            line.startswith("|")
            and i + 1 < len(lines)
            and TABLE_SEP_RE.match(_strip_eol(lines[i + 1]))
        ):
            table, i = _parse_table_at(lines, i)
            table.section = current_section
            doc.tables.append(table)
            continue
        i += 1
    return doc


def _parse_record(lines: list[str], i: int, path: str | None) -> tuple[Record, int]:
    head = _strip_eol(lines[i])
    m = RECORD_HEAD_RE.match(head)
    if not m:
        raise RecordParseError(
            f"malformed record heading {head!r} (expected '### <ID> — <title>')", i + 1, path
        )
    record_id = m.group("id")
    if ids.parse(record_id, strict=False) is None:
        raise RecordParseError(f"unknown record prefix in {record_id!r}", i + 1, path)
    rec = Record(id=record_id, title=m.group("title"), start=i)
    last_key: str | None = None
    j = i + 1
    while j < len(lines):
        line = _strip_eol(lines[j])
        if line.startswith("- "):
            fm = FIELD_RE.match(line)
            if not fm:
                raise RecordParseError(f"malformed field line {line!r}", j + 1, path)
            key = fm.group("key")
            if key in rec.fields:
                raise RecordParseError(f"duplicate field {key!r} in {record_id}", j + 1, path)
            rec.set(key, fm.group("value") or "")
            last_key = key
        elif line.startswith("  "):
            if last_key is None:
                raise RecordParseError(
                    f"continuation line before any field in {record_id}", j + 1, path
                )
            rec.fields[last_key] += "\n" + line[2:]
        else:
            break
        j += 1
    rec.end = j
    return rec, j


def serialize_record(rec: Record) -> str:
    """Canonical text for one record, ending with a newline."""
    out = [f"### {rec.id} — {rec.title}"]
    for key in rec.order:
        parts = rec.fields[key].split("\n")
        out.append(f"- {key}:" + (f" {parts[0]}" if parts[0] else ""))
        out.extend(f"  {p}" for p in parts[1:])
    return "\n".join(out) + "\n"


def serialize_document(doc: Document, replacements: dict[str, Record] | None = None) -> str:
    """Rebuild the document; records are re-serialised (optionally replaced by id)."""
    replacements = replacements or {}
    out: list[str] = []
    cursor = 0
    for rec in doc.records:
        out.extend(doc.lines[cursor : rec.start])
        out.append(serialize_record(replacements.get(rec.id, rec)))
        cursor = rec.end
    out.extend(doc.lines[cursor:])
    return "".join(out)


def append_records(text: str, records: list[Record], section: str | None = None) -> str:
    """Append ``records`` to ``text``, preserving all existing content byte-for-byte.

    With ``section`` (e.g. ``"## Records"``), records go at the end of that section
    (before the next heading of the same or higher level); the section is created at
    the end of the document if missing. Records are separated by blank lines.
    """
    if not records:
        return text
    block = "\n".join(serialize_record(r) for r in records)
    if text and not text.endswith("\n"):
        text += "\n"
    lines = text.splitlines(keepends=True)

    def joined(before: list[str], after: list[str]) -> str:
        prefix = "".join(before)
        if prefix and not prefix.endswith("\n\n"):
            prefix += "\n"
        suffix = "".join(after)
        return prefix + block + ("\n" + suffix if suffix else "")

    if section is None:
        return joined(lines, [])
    level = len(section) - len(section.lstrip("#"))
    in_fence = False
    for idx, raw in enumerate(lines):
        line = _strip_eol(raw)
        if FENCE_RE.match(line):
            in_fence = not in_fence
        if not in_fence and line == section:
            end = len(lines)
            fence = False
            for k in range(idx + 1, len(lines)):
                nxt = _strip_eol(lines[k])
                if FENCE_RE.match(nxt):
                    fence = not fence
                h = HEADING_RE.match(nxt)
                if not fence and h and len(h.group("hashes")) <= level:
                    end = k
                    break
            return joined(lines[:end], lines[end:])
    # Section missing: create it at the end of the document.
    prefix = "".join(lines)
    if prefix and not prefix.endswith("\n\n"):
        prefix += "\n"
    return prefix + section + "\n\n" + block


def parse_refs(value: str, known_only: bool = True) -> list[str]:
    """IDs referenced in a field value, in order of first appearance, de-duplicated.

    Only IDs with a known prefix are returned (so ``UTF-8`` is not a reference).
    Provisional IDs (``D-?7``) are included.
    """
    seen: list[str] = []
    for m in ids.ANY_ID_RE.finditer(value):
        token = m.group(0)
        if known_only and ids.parse(token, strict=False) is None:
            continue
        if token not in seen:
            seen.append(token)
    return seen


def _split_cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return [c.strip() for c in CELL_SPLIT_RE.split(body)]


def _parse_table_at(lines: list[str], i: int) -> tuple[Table, int]:
    headers = _split_cells(_strip_eol(lines[i]))
    rows: list[list[str]] = []
    j = i + 2
    while j < len(lines) and _strip_eol(lines[j]).startswith("|"):
        rows.append(_split_cells(_strip_eol(lines[j])))
        j += 1
    return Table(headers=headers, rows=rows, start=i, end=j), j


def parse_table(section_text: str) -> Table | None:
    """The first GFM table found in ``section_text`` (outside code fences), or None."""
    doc = parse_document(section_text)
    return doc.tables[0] if doc.tables else None


def serialize_table(table: Table) -> str:
    def row(cells: list[str]) -> str:
        return "| " + " | ".join(cells) + " |"

    out = [row(table.headers), "|" + "|".join("---" for _ in table.headers) + "|"]
    out.extend(row(r) for r in table.rows)
    return "\n".join(out) + "\n"


_STOPWORDS = frozenset(
    "a an the of to in on for and or is are be can by with as at from it its this that".split()
)
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalise_text(value: str) -> str:
    """Dedupe form of free text: lowercase, punctuation → space, stopwords dropped."""
    words = _NON_ALNUM_RE.sub(" ", value.lower()).split()
    return " ".join(w for w in words if w not in _STOPWORDS)
