"""Staging → canonical merge.

``merge`` is the ONLY writer of canonical record files. For one staging run it:

1. reads every staged ``.md`` (layout mirrors the workspace; ``raw/`` and dotfiles skipped),
2. maps each provisional record (``D-?3``) to an existing canonical record with the same
   dedupe key — unioning its reference-list fields instead of duplicating — or to a newly
   allocated final ID (never reusing numbers: see ``workspace.load_id_marks``),
3. rewrites every provisional reference in staged records, record files and documents,
4. writes canonical files atomically, all-or-nothing: any error aborts before writing,
5. archives the run under ``staging/_merged/<run-id>/`` and logs a history event.
"""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pflib import catalog, ids, records, render, workspace
from pflib.catalog import ArtifactSpec, RecordSchema
from pflib.errors import CheckFailed, UsageError
from pflib.index import WorkspaceIndex
from pflib.io import atomic_write_text
from pflib.records import Document, Record


class MergeError(CheckFailed):
    """A merge was refused; nothing was written."""


@dataclass
class StagedRecord:
    rel: str  # staged path relative to the run dir (== canonical path for records kind)
    spec: ArtifactSpec
    schema: RecordSchema
    record: Record
    order: int  # global processing order for determinism


@dataclass
class MergeReport:
    run_id: str
    added: dict[str, int] = field(default_factory=dict)
    deduped: int = 0
    id_map: dict[str, str] = field(default_factory=dict)
    new_ids: list[str] = field(default_factory=list)  # final IDs allocated by this merge
    files_written: list[str] = field(default_factory=list)
    documents_updated: list[str] = field(default_factory=list)
    conflicts: list[dict[str, str]] = field(default_factory=list)
    ignored_prose_lines: int = 0
    amended: list[str] = field(default_factory=list)  # existing records changed by amendments
    sections_updated: list[str] = field(default_factory=list)  # prose sections in record files
    rendered: list[str] = field(default_factory=list)  # artifacts whose generated views changed
    dropped: list[str] = field(default_factory=list)  # new sources dropped by research.max_sources
    over_cap: int = 0  # sources still above the cap (kept because other records cite them)
    documents_removed: list[str] = field(default_factory=list)  # REMOVE_MARKER documents
    revised: list[str] = field(default_factory=list)  # record files whose body was revised

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "added": self.added,
            "deduped": self.deduped,
            "id_map": self.id_map,
            "new_ids": self.new_ids,
            "files_written": self.files_written,
            "documents_updated": self.documents_updated,
            "conflicts": self.conflicts,
            "ignored_prose_lines": self.ignored_prose_lines,
            "amended": self.amended,
            "sections_updated": self.sections_updated,
            "rendered": self.rendered,
            "dropped": self.dropped,
            "documents_removed": self.documents_removed,
            "revised": self.revised,
            "over_cap": self.over_cap,
        }


# --------------------------------------------------------------------------- helpers


def rewrite_provisional(text: str, mapping: dict[str, str]) -> str:
    return ids.PROVISIONAL_RE.sub(lambda m: mapping.get(m.group(0), m.group(0)), text)


def provisional_refs(text: str) -> set[str]:
    return {m.group(0) for m in ids.PROVISIONAL_RE.finditer(text)}


def _host(value: str) -> str:
    try:
        host = urlsplit(value.strip()).hostname or value.strip().lower()
    except ValueError:
        host = value.strip().lower()
    return host[4:] if host.startswith("www.") else host


def dedupe_key(
    schema: RecordSchema, rec: Record, mapping: dict[str, str]
) -> tuple[str, ...] | None:
    parts: list[str] = []
    for name in schema.dedupe:
        raw = rec.title if name == catalog.TITLE else rec.get(name)
        raw = rewrite_provisional(raw, mapping)
        if schema.dedupe_mode == catalog.DEDUPE_NORMALISED:
            parts.append(records.normalise_text(raw))
        elif schema.dedupe_mode == catalog.DEDUPE_HOST:
            parts.append(_host(raw))
        else:
            parts.append(raw.strip())
    if all(p == "" for p in parts):
        return None
    return tuple(parts)


def _copy(rec: Record) -> Record:
    return Record(
        rec.id, rec.title, dict(rec.fields), list(rec.order), rec.start, rec.end, rec.section
    )


def _rewritten(rec: Record, mapping: dict[str, str], new_id: str | None = None) -> Record:
    out = _copy(rec)
    out.id = new_id or rewrite_provisional(rec.id, mapping)
    out.title = rewrite_provisional(rec.title, mapping)
    out.fields = {k: rewrite_provisional(v, mapping) for k, v in rec.fields.items()}
    return out


def union_into(
    target: Record, incoming: Record, schema: RecordSchema, report: MergeReport
) -> Record:
    """Union ``incoming``'s reference-list fields into ``target`` (both already rewritten).

    Existing text is preserved; only IDs not already present are appended. Differences in
    non-union fields are kept as they are in ``target`` and reported as conflicts.
    """
    out = _copy(target)
    for key in schema.union_fields:
        new_refs = records.parse_refs(incoming.get(key))
        have = records.parse_refs(out.get(key))
        extra = [r for r in new_refs if r not in have]
        if extra:
            current = out.get(key).strip()
            out.set(key, ", ".join(([current] if current else []) + extra))
    for key in schema.fields:
        if key in schema.union_fields:
            continue
        theirs = incoming.get(key).strip()
        mine = out.get(key).strip()
        if theirs and records.normalise_text(theirs) != records.normalise_text(mine):
            report.conflicts.append({"id": out.id, "field": key, "kept": mine, "staged": theirs})
    return out


@contextmanager
def merge_lock(ws: Path) -> Iterator[None]:
    path = workspace.pf_dir(ws) / workspace.MERGE_LOCK
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise MergeError(
            f"another merge is in progress ({path} exists; delete it if no merge is running)",
            code="MERGE_LOCKED",
        ) from None
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def _level2_blocks(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Split a document into (preamble, [(heading line, block text incl. heading)])."""
    doc = records.parse_document(text)
    heads = [s for s in doc.sections if s.level <= 2]
    if not heads:
        return text, []
    preamble = "".join(doc.lines[: heads[0].start])
    blocks: list[tuple[str, str]] = []
    for i, sec in enumerate(heads):
        end = heads[i + 1].start if i + 1 < len(heads) else len(doc.lines)
        heading = records._strip_eol(doc.lines[sec.start])
        blocks.append((heading, "".join(doc.lines[sec.start : end])))
    return preamble, blocks


def _bullet_key(line: str) -> str | None:
    if line.startswith("- ") and ":" in line:
        return line[2:].split(":", 1)[0].strip().lower()
    return None


def merge_keyed_block(canonical: str, staged: str) -> str:
    """``- key: value`` lines: a staged line replaces its key's canonical line, new keys are
    appended after the last bullet, and every other canonical line is kept."""
    canon_lines = canonical.splitlines(keepends=True)
    staged_by_key: dict[str, str] = {}
    for line in staged.splitlines(keepends=True):
        key = _bullet_key(line)
        if key is not None:
            staged_by_key[key] = line if line.endswith("\n") else line + "\n"
    out: list[str] = []
    seen: set[str] = set()
    last_bullet = -1
    for line in canon_lines:
        key = _bullet_key(line)
        if key is not None:
            out.append(staged_by_key.get(key, line))
            seen.add(key)
            last_bullet = len(out) - 1
        else:
            out.append(line)
    new = [line for key, line in staged_by_key.items() if key not in seen]
    if new:
        at = last_bullet + 1 if last_bullet >= 0 else len(out)
        out[at:at] = new
    return "".join(out)


def merge_document_sections(canonical: str | None, staged: str, keyed: tuple[str, ...] = ()) -> str:
    """Section-level document merge: staged ``#``/``##`` sections replace same-named
    canonical sections, new ones are appended; a missing canonical file is created as-is.
    Sections named in ``keyed`` merge line by line on their ``- key:`` bullets."""
    if canonical is None:
        return staged
    _, staged_blocks = _level2_blocks(staged)
    preamble, canon_blocks = _level2_blocks(canonical)
    index = {heading: i for i, (heading, _) in enumerate(canon_blocks)}
    merged = list(canon_blocks)
    for heading, block in staged_blocks:
        block = block if block.endswith("\n") else block + "\n"
        if heading in index and heading.lstrip("#").strip() in keyed:
            merged[index[heading]] = (heading, merge_keyed_block(merged[index[heading]][1], block))
        elif heading in index:
            old = merged[index[heading]][1]
            # keep the canonical spacing before the next section
            trailing = old[len(old.rstrip("\n")) :]
            merged[index[heading]] = (heading, block.rstrip("\n") + (trailing or "\n"))
        else:
            if merged and not merged[-1][1].endswith("\n\n"):
                last_h, last_b = merged[-1]
                merged[-1] = (last_h, last_b.rstrip("\n") + "\n\n")
            elif not merged and preamble and not preamble.endswith("\n\n"):
                preamble = preamble.rstrip("\n") + "\n\n"
            merged.append((heading, block))
            index[heading] = len(merged) - 1
    return preamble + "".join(b for _, b in merged)


# --------------------------------------------------------------------------- merge


@dataclass
class StagedAmendment:
    rel: str
    amendment: records.Amendment


REVISE_RE = re.compile(
    r"^### REVISE (?P<id>[A-Z]{1,3}-\d+)\s*\n(?P<why>- Why:[^\n]*\n)?(?P<body>.*)\Z", re.S
)
REVISE_HEADING_RE = re.compile(r"^### REVISE\b", re.M)


@dataclass
class StagedRevision:
    """A new body for an existing record file (v1.1 dogfood: workflows could not take new
    evidence — a re-staged workflow only unioned its header IDs and lost the rewritten steps)."""

    rel: str
    target: str
    why: str
    body: str


def parse_revision(rel: str, text: str) -> StagedRevision | None:
    m = REVISE_RE.match(text.lstrip("\n"))
    if not m:
        return None
    why = (m.group("why") or "")[len("- Why:") :].strip()
    return StagedRevision(rel, m.group("id"), why, m.group("body"))


def _record_file_body_lines(text: str) -> int:
    """Non-blank, non-heading lines after a record file's header record."""
    body = text.split("\n## ", 1)[1] if "\n## " in text else ""
    return sum(1 for ln in body.splitlines()[1:] if ln.strip() and not ln.startswith("#"))


def _prose_sections(doc: Document, spec: ArtifactSpec) -> str:
    """Staged ``##`` sections of a records-kind file that hold no records, are not a schema's
    record section and contain no generated region (e.g. ``## Domains``) — merged like documents."""
    record_sections = {s.section for s in spec.schemas if s.section}
    heads = [s for s in doc.sections if s.level <= 2]
    out: list[str] = []
    for i, sec in enumerate(heads):
        end = heads[i + 1].start if i + 1 < len(heads) else len(doc.lines)
        block = "".join(doc.lines[sec.start : end])
        has_records = any(sec.start <= r.start < end for r in doc.records)
        if sec.level != 2 or has_records or f"## {sec.title}" in record_sections:
            continue
        if "pf:generated:start" in block:
            continue
        out.append(block if block.endswith("\n") else block + "\n")
    return "".join(out)


def _collect(
    run_dir: Path, revisions: list[StagedRevision] | None = None
) -> tuple[
    list[StagedRecord], dict[str, str], dict[str, str], int, list[StagedAmendment], dict[str, str]
]:
    """Returns (records, record-file texts, documents, prose lines, amendments, prose sections);
    record-file revisions (``### REVISE <ID>``) are appended to ``revisions``."""
    amendments: list[StagedAmendment] = []
    sections: dict[str, str] = {}
    staged: list[StagedRecord] = []
    record_files: dict[str, str] = {}
    documents: dict[str, str] = {}
    prose = 0
    seen: dict[str, str] = {}
    order = 0
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(run_dir).as_posix()
        parts = rel.split("/")
        if parts[0] == workspace.RAW or any(part.startswith(".") for part in parts):
            continue
        spec = catalog.spec_for_staged_path(rel)
        if spec is None or not rel.endswith(".md"):
            raise MergeError(
                f"staged file {rel} does not map to any artifact in the catalog",
                code="UNKNOWN_ARTIFACT",
                details={"file": rel},
            )
        text = path.read_text(encoding="utf-8")
        if spec.kind == catalog.KIND_DOCUMENT:
            documents[rel] = text
            continue
        if text.strip() == REMOVE_MARKER:
            raise MergeError(f"{rel}: record files cannot be removed (supersede records instead)",
                             code="BAD_REMOVE", details={"file": rel})  # fmt: skip
        revision = parse_revision(rel, text) if spec.kind == catalog.KIND_RECORD_FILE else None
        if revision is not None:
            if revisions is None:
                raise MergeError(f"{rel}: revisions are not accepted here", code="BAD_REVISION")
            revisions.append(revision)
            continue
        if spec.kind != catalog.KIND_RECORD_FILE and REVISE_HEADING_RE.search(text):
            # v1.1 dogfood: a REVISE here used to pass as prose, and its corrections vanished
            raise MergeError(
                f"{rel}: `### REVISE` changes record files only (one record per file: workflows, "
                f"ADRs, phases); records in {spec.title} change by stage-and-supersede — stage the "
                "corrected record with a provisional ID and `### AMEND <old ID>` with "
                "`- Status: superseded-by <provisional ID>` and a `- Why:` line",
                code="BAD_REVISION",
                details={"file": rel},
            )
        found = records.parse_amendments(text, path=rel)
        amendments.extend(StagedAmendment(rel, a) for a in found)
        if found:  # amendment blocks are not prose
            kept = text.splitlines(keepends=True)
            for a in reversed(found):
                del kept[a.start : a.end]
            text = "".join(kept)
        doc = records.parse_document(text, path=rel)
        if spec.kind == catalog.KIND_RECORD_FILE:
            if len(doc.records) != 1:
                raise MergeError(
                    f"{rel}: a {spec.title.lower()} file must hold exactly one record "
                    f"(found {len(doc.records)})",
                    code="BAD_RECORD_FILE",
                    details={"file": rel},
                )
            record_files[rel] = text
        else:
            block = _prose_sections(doc, spec)
            if block:
                sections[rel] = block
            merged_lines = [
                ln for ln in block.splitlines() if ln.strip() and not ln.startswith("#")
            ]
            prose += _count_prose(doc) - len(merged_lines)  # headings are never counted as prose
        for rec in doc.records:
            parsed = ids.parse(rec.id)
            assert parsed is not None
            if not parsed.provisional:
                raise MergeError(
                    f"{rel}: staged record {rec.id} uses a final ID; staged records "
                    f"must use provisional IDs like {parsed.prefix}-?1",
                    code="STAGED_FINAL_ID",
                    details={"file": rel, "id": rec.id},
                )
            schema = spec.schema(parsed.prefix)
            if schema is None:
                raise MergeError(
                    f"{rel}: records with prefix {parsed.prefix} do not belong in {spec.path}",
                    code="WRONG_ARTIFACT",
                    details={"file": rel, "id": rec.id},
                )
            if rec.id in seen:
                raise MergeError(
                    f"provisional id {rec.id} defined twice ({seen[rec.id]} and {rel})",
                    code="DUPLICATE_ID",
                    details={"id": rec.id},
                )
            seen[rec.id] = rel
            staged.append(StagedRecord(rel, spec, schema, rec, order))
            order += 1
    return staged, record_files, documents, prose, amendments, sections


def _count_prose(doc: Document) -> int:
    covered: set[int] = set()
    for rec in doc.records:
        covered.update(range(rec.start, rec.end))
    for sec in doc.sections:
        covered.add(sec.start)
    return sum(1 for i, line in enumerate(doc.lines) if i not in covered and line.strip())


def _apply_source_cap(
    ws: Path,
    staged: list[StagedRecord],
    record_files: dict[str, str],
    documents: dict[str, str],
    index: WorkspaceIndex,
    report: MergeReport,
) -> list[StagedRecord]:
    """Enforce ``research.max_sources``: drop new, *unreferenced* staged sources (last first).

    Sources that other staged records cite are kept even over the cap (dropping them would leave
    dangling references); the excess is reported as ``over_cap``.
    """
    from pflib import config

    cap = int(config.resolve("research.max_sources", ws))
    existing = index.records("S")
    if not existing and not any(sr.schema.prefix == "S" for sr in staged):
        return staged
    _, schema = catalog.schema_for_prefix("S")
    canonical_keys = {dedupe_key(schema, rec, {}) for _, rec in existing}
    new: list[StagedRecord] = []
    seen_keys: set[tuple[str, ...] | None] = set()
    for sr in staged:
        if sr.schema.prefix != "S":
            continue
        key = dedupe_key(sr.schema, sr.record, {})
        if key is not None and (key in canonical_keys or key in seen_keys):
            continue
        seen_keys.add(key)
        new.append(sr)
    # only this run's new sources count: a workspace already over the cap (a lowered knob) must
    # not report its old excess on every merge (v1.1 dogfood: over_cap 48 on a scope run)
    excess = min(len(new), len(existing) + len(new) - cap)
    if excess <= 0:
        return staged
    texts = [records.serialize_record(sr.record) for sr in staged]
    texts += list(record_files.values()) + list(documents.values())
    drop: set[str] = set()
    for sr in reversed(new):
        if len(drop) == excess:
            break
        own = records.serialize_record(sr.record)
        cited = any(sr.record.id in provisional_refs(t) for t in texts if t != own)
        if not cited:
            drop.add(sr.record.id)
    report.dropped = sorted(drop, key=lambda i: int(i.split("?")[1]))
    report.over_cap = excess - len(drop)
    return [sr for sr in staged if sr.record.id not in drop]


def _apply_revisions(
    ws: Path,
    revisions: list[StagedRevision],
    mapping: dict[str, str],
    index: WorkspaceIndex,
    outputs: dict[str, str],
    current_text: Callable[[str, ArtifactSpec], str],
    report: MergeReport,
) -> list[dict[str, Any]]:
    """Replace body sections of existing record files of the open stage (all-or-nothing)."""
    if not revisions:
        return []
    from pflib import state

    open_stage = state.load(ws).state.value
    located = []
    for rv in revisions:
        parsed = ids.parse(rv.target, strict=False)
        hit = next(((rel, rec) for rel, rec in index.records(parsed.prefix) if rec.id == rv.target),
                   None) if parsed else None  # fmt: skip
        if hit is None:
            raise MergeError(f"{rv.rel}: revision target {rv.target} does not exist",
                             code="REVISE_TARGET_MISSING", details={"id": rv.target})  # fmt: skip
        rel, _ = hit
        spec = catalog.spec_for_path(rel)
        assert spec is not None and parsed is not None
        if spec.kind != catalog.KIND_RECORD_FILE:
            raise MergeError(f"{rv.rel}: {rv.target} is not a record file; use an amendment",
                             code="BAD_REVISION", details={"id": rv.target})  # fmt: skip
        owner = spec.owner_of(parsed.prefix)
        if owner != open_stage:
            raise MergeError(
                f"{rv.rel}: {rv.target} belongs to {owner}, which is not the open stage "
                f"({open_stage}); use `pf.py reopen {owner}` to change it",
                code="REVISE_LOCKED", details={"id": rv.target, "owner": owner},
            )  # fmt: skip
        if not rv.why:
            raise MergeError(f"{rv.rel}: revision of {rv.target} needs a `- Why:` line",
                             code="REVISE_NO_REASON", details={"id": rv.target})  # fmt: skip
        if "\n## " not in "\n" + rv.body:
            raise MergeError(f"{rv.rel}: revision of {rv.target} holds no `## ` section",
                             code="BAD_REVISION", details={"id": rv.target})  # fmt: skip
        located.append((rv, rel, spec))
    events = []
    for rv, rel, spec in located:
        body = rewrite_provisional(rv.body, mapping)
        outputs[rel] = merge_document_sections(current_text(rel, spec), body)
        report.revised.append(rv.target)
        sections_changed = [ln[3:].strip() for ln in body.splitlines() if ln.startswith("## ")]
        events.append({"id": rv.target, "sections": sections_changed, "why": rv.why})
    return events


def _apply_amendments(
    ws: Path,
    amendments: list[StagedAmendment],
    mapping: dict[str, str],
    index: WorkspaceIndex,
    outputs: dict[str, str],
    current_text: Callable[[str, ArtifactSpec], str],
    report: MergeReport,
) -> list[dict[str, Any]]:
    """Validate every amendment first (all-or-nothing), then apply them to ``outputs``."""
    if not amendments:
        return []
    from pflib import state

    try:
        open_stage = state.load(ws).state.value
    except CheckFailed as exc:
        raise MergeError("amendments need a workspace state.json", code="AMEND_LOCKED") from exc
    located: list[tuple[StagedAmendment, str, ArtifactSpec, Record]] = []
    for sa in amendments:
        a = sa.amendment
        where = f"{sa.rel}:{a.line}"
        parsed = ids.parse(a.target, strict=False)
        hit = None
        if parsed is not None:
            candidates = index.records(parsed.prefix)
            hit = next(((rel, rec) for rel, rec in candidates if rec.id == a.target), None)
        if hit is None:
            raise MergeError(f"{where}: amendment target {a.target} does not exist",
                             code="AMEND_TARGET_MISSING", details={"id": a.target})  # fmt: skip
        rel, rec = hit
        spec = catalog.spec_for_path(rel)
        assert spec is not None and parsed is not None
        owner = spec.owner_of(parsed.prefix)
        if owner != open_stage:
            raise MergeError(
                f"{where}: {a.target} belongs to {owner}, which is not the open stage "
                f"({open_stage}); use `pf.py reopen {owner}` to change it",
                code="AMEND_LOCKED", details={"id": a.target, "owner": owner},
            )  # fmt: skip
        changes = {k: v for k, v in a.fields.items() if k != "Why"}
        allowed = records.amendable(a.target)
        bad = sorted(set(changes) - set(allowed))
        if bad or not changes:
            raise MergeError(
                f"{where}: amendments of {a.target} may only set {', '.join(allowed)} "
                f"(got {', '.join(bad) or 'nothing'})",
                code="AMEND_FIELD_NOT_ALLOWED", details={"id": a.target, "fields": bad},
            )  # fmt: skip
        if not a.fields.get("Why", "").strip():
            raise MergeError(f"{where}: amendment of {a.target} needs a `- Why:` line",
                             code="AMEND_NO_REASON", details={"id": a.target})  # fmt: skip
        located.append((sa, rel, spec, rec))
    events: list[dict[str, Any]] = []
    for sa, rel, spec, rec in located:
        doc = records.parse_document(current_text(rel, spec), path=rel)
        current = doc.record(rec.id)
        assert current is not None
        updated = _copy(current)
        changes = {
            k: rewrite_provisional(v, mapping) for k, v in sa.amendment.fields.items() if k != "Why"
        }
        for key, value in changes.items():
            updated.set(key, value)
        outputs[rel] = records.serialize_document(doc, {rec.id: updated})
        report.amended.append(rec.id)
        events.append({"id": rec.id, "fields": changes, "why": sa.amendment.fields["Why"].strip()})
    return events


def _skeleton(ws: Path, rel: str, spec: ArtifactSpec) -> str:
    """Starting text of a canonical file merge creates: its template, else a bare heading."""
    from pflib import scaffold  # scaffold imports state; keep merge's import graph small

    seeded = scaffold.seed_text(ws, rel)
    return seeded if seeded is not None else f"# {spec.title}\n"


REMOVE_MARKER = "<!-- pf:remove -->"


def _check_removable(ws: Path, rel: str) -> None:
    """Only documents (never record files) of the open stage may be removed."""
    from pflib import state

    spec = catalog.spec_for_path(rel)
    open_stage = state.load(ws).state.value
    if spec is None or spec.kind != catalog.KIND_DOCUMENT or spec.owner_stage != open_stage:
        raise MergeError(
            f"{rel}: only documents of the open stage ({open_stage}) can be removed",
            code="BAD_REMOVE",
            details={"file": rel},
        )


def merge(ws: Path, run_id: str) -> MergeReport:
    run_dir = workspace.staging_dir(ws, run_id)
    if not run_dir.is_dir():
        raise UsageError(f"no staging run {run_id!r}", code="NO_SUCH_RUN")
    archive = workspace.staging_root(ws) / workspace.MERGED / run_id
    if archive.exists():
        raise MergeError(f"run {run_id} was already merged", code="ALREADY_MERGED")

    with merge_lock(ws):
        report = MergeReport(run_id=run_id)
        revisions: list[StagedRevision] = []
        staged, record_files, documents, report.ignored_prose_lines, amendments, sections = (
            _collect(run_dir, revisions)
        )
        index = WorkspaceIndex(ws)
        staged = _apply_source_cap(ws, staged, record_files, documents, index, report)
        marks = workspace.load_id_marks(ws)

        # Records whose dedupe key references other records go last, so the records they
        # reference are already mapped (e.g. an FS keyed on a brand-new F).
        def key_depends_on_refs(sr: StagedRecord) -> bool:
            return bool(set(sr.schema.dedupe) & set(sr.schema.ref_fields))

        ordered = sorted(staged, key=lambda sr: (key_depends_on_refs(sr), sr.order))

        mapping: dict[str, str] = {}
        canon_keys: dict[str, dict[tuple[str, ...], tuple[str, Record]]] = {}
        next_num: dict[str, int] = {}
        primaries: dict[str, StagedRecord] = {}  # final id → first staged record
        staged_unions: dict[str, list[StagedRecord]] = {}  # final id (new) → duplicates
        canon_unions: dict[str, list[StagedRecord]] = {}  # final id (existing) → staged
        run_keys: dict[tuple[str, tuple[str, ...]], str] = {}

        for sr in ordered:
            prefix = sr.schema.prefix
            if prefix not in canon_keys:
                canon_keys[prefix] = {}
                existing = index.records(prefix)
                for rel, rec in existing:
                    k = dedupe_key(sr.schema, rec, {})
                    if k is not None:
                        canon_keys[prefix].setdefault(k, (rel, rec))
                next_num[prefix] = max(
                    ids.max_id(prefix, (r.id for _, r in existing)), marks.get(prefix, 0)
                )
            key = dedupe_key(sr.schema, sr.record, mapping)
            if key is not None and key in canon_keys[prefix]:
                final = canon_keys[prefix][key][1].id
                canon_unions.setdefault(final, []).append(sr)
            elif key is not None and (prefix, key) in run_keys:
                final = run_keys[(prefix, key)]
                staged_unions.setdefault(final, []).append(sr)
            else:
                final = ""
            if final:
                report.deduped += 1
                if sr.spec.kind == catalog.KIND_RECORD_FILE:
                    # only the header record unions; the duplicate file's body is not merged
                    report.ignored_prose_lines += _record_file_body_lines(record_files[sr.rel])
            else:
                next_num[prefix] += 1
                final = ids.format_id(prefix, next_num[prefix])
                primaries[final] = sr
                report.new_ids.append(final)
                report.added[prefix] = report.added.get(prefix, 0) + 1
                if key is not None:
                    run_keys[(prefix, key)] = final
            mapping[sr.record.id] = final

        # Every provisional reference anywhere in the run must resolve.
        texts = [records.serialize_record(sr.record) for sr in staged]
        texts += list(record_files.values()) + list(documents.values())
        texts += ["\n".join(sa.amendment.fields.values()) for sa in amendments]
        texts += list(sections.values())
        texts += [rv.body for rv in revisions]
        dangling = sorted(set().union(*(provisional_refs(t) for t in texts)) - set(mapping))
        if dangling:
            raise MergeError(
                f"provisional references with no staged definition: {', '.join(dangling)}",
                code="DANGLING_PROVISIONAL",
                details={"ids": dangling},
            )
        report.id_map = {sr.record.id: mapping[sr.record.id] for sr in staged}

        outputs: dict[str, str] = {}

        def current_text(rel: str, spec: ArtifactSpec) -> str:
            if rel in outputs:
                return outputs[rel]
            path = ws / rel
            return path.read_text(encoding="utf-8") if path.is_file() else _skeleton(ws, rel, spec)

        # 1) unions into existing canonical records
        canon_by_id = {
            rec.id: (rel, rec) for keys in canon_keys.values() for rel, rec in keys.values()
        }
        for final, srs in sorted(canon_unions.items()):
            rel, rec = canon_by_id[final]
            updated = rec
            for sr in srs:
                updated = union_into(updated, _rewritten(sr.record, mapping), sr.schema, report)
            if updated.fields != rec.fields:
                spec = srs[0].spec
                doc = records.parse_document(current_text(rel, spec), path=rel)
                outputs[rel] = records.serialize_document(doc, {final: updated})

        # 2) new records
        for final, sr in sorted(primaries.items(), key=lambda kv: kv[1].order):
            new_rec = _rewritten(sr.record, mapping, new_id=final)
            for dup in staged_unions.get(final, []):
                new_rec = union_into(new_rec, _rewritten(dup.record, mapping), sr.schema, report)
            if sr.spec.kind == catalog.KIND_RECORD_FILE:
                rel = catalog.record_file_path(sr.spec, final, new_rec.title)
                body = rewrite_provisional(record_files[sr.rel], mapping)
                doc = records.parse_document(body, path=rel)
                outputs[rel] = records.serialize_document(doc, {doc.records[0].id: new_rec})
            else:
                rel = sr.rel
                outputs[rel] = records.append_records(
                    current_text(rel, sr.spec), [new_rec], sr.schema.section
                )

        # 3) amendments to existing records of the open stage
        amend_events = _apply_amendments(
            ws, amendments, mapping, index, outputs, current_text, report
        )
        revise_events = _apply_revisions(
            ws, revisions, mapping, index, outputs, current_text, report
        )

        # 4) prose sections inside records-kind files (e.g. "## Domains")
        for rel, block in sorted(sections.items()):
            section_spec = catalog.spec_for_staged_path(rel)
            assert section_spec is not None
            outputs[rel] = merge_document_sections(
                current_text(rel, section_spec), rewrite_provisional(block, mapping)
            )
            report.sections_updated.append(rel)

        # 5) documents (section-level merge; REMOVE_MARKER deletes an open-stage document)
        removals: list[str] = []
        for rel, text in sorted(documents.items()):
            path = ws / rel
            if text.strip() == REMOVE_MARKER:
                _check_removable(ws, rel)
                if path.is_file():
                    removals.append(rel)
                continue
            canonical = path.read_text(encoding="utf-8") if path.is_file() else None
            outputs[rel] = merge_document_sections(
                canonical, rewrite_provisional(text, mapping), catalog.KEYED_SECTIONS.get(rel, ())
            )
            report.documents_updated.append(rel)

        # Validate every output parses before touching the disk (all-or-nothing).
        for rel, text in outputs.items():
            records.parse_document(text, path=rel)

        for rel, text in sorted(outputs.items()):
            target = ws / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(target, text)
            report.files_written.append(rel)
        for rel in removals:
            (ws / rel).unlink()
            report.documents_removed.append(rel)

        report.rendered = render.render_all(ws)
        for event in amend_events:
            workspace.append_history(ws, {"event": "amend", "run_id": run_id, **event})
        for event in revise_events:
            workspace.append_history(ws, {"event": "revise", "run_id": run_id, **event})
        for prefix, number in next_num.items():
            marks[prefix] = max(marks.get(prefix, 0), number)
        workspace.save_id_marks(ws, marks)
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(run_dir), str(archive))
        workspace.append_history(
            ws,
            {
                "event": "merge",
                "run_id": run_id,
                "added": report.added,
                "deduped": report.deduped,
                "files": report.files_written,
                "conflicts": len(report.conflicts),
            },
        )
        return report


def allocate_next(ws: Path, prefix: str) -> str:
    """Allocate one final ID for sequential single-writer use (``pf.py next-id``)."""
    ids.check_prefix(prefix)
    with merge_lock(ws):
        marks = workspace.load_id_marks(ws)
        (new_id,) = ids.allocate(
            prefix, 1, WorkspaceIndex(ws).ids(prefix), floor=marks.get(prefix, 0)
        )
        parsed = ids.parse(new_id)
        assert parsed is not None
        marks[prefix] = parsed.number
        workspace.save_id_marks(ws, marks)
        workspace.append_history(ws, {"event": "next-id", "id": new_id})
        return new_id


def _preflight_ignore(directory: str, names: list[str]) -> set[str]:
    return {n for n in names if n in (*workspace.ARCHIVES, "cache")}


def preflight(ws: Path, run_id: str) -> dict[str, Any]:
    """Merge ``run_id`` into a throw-away copy of the workspace and validate the result.

    Nothing in ``ws`` changes. Returns the would-be merge report and the validator findings
    that concern this run's records (new or deduped-into) or the files it would write — the
    input for an agent repair loop *before* anything reaches the canonical files.
    """
    import tempfile

    from pflib import validators

    run_dir = workspace.staging_dir(ws, run_id)
    if not run_dir.is_dir():
        raise UsageError(f"no staging run {run_id!r}", code="NO_SUCH_RUN")
    with tempfile.TemporaryDirectory(prefix="pf-preflight-") as tmp:
        copy = Path(tmp) / "ws"
        shutil.copytree(ws, copy, ignore=_preflight_ignore)
        (workspace.pf_dir(copy) / workspace.MERGE_LOCK).unlink(missing_ok=True)
        try:
            report = merge(copy, run_id)
        except MergeError as exc:
            return {"run_id": run_id, "ok": False, "merge_error": exc.to_dict(), "report": None,
                    "errors": 1, "warnings": 0, "findings": []}  # fmt: skip
        touched = set(report.id_map.values())
        written = set(report.files_written)
        found = [
            f
            for f in validators.run(copy)
            if f.record_id in touched or (f.record_id is None and f.artifact in written)
        ]
    summary = validators.summary(found)
    return {
        "run_id": run_id,
        "ok": summary["errors"] == 0,
        "merge_error": None,
        "report": report.to_dict(),
        **summary,
    }
