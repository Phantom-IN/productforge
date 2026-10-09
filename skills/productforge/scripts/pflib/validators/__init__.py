"""Validator framework (IMPLEMENTATION_PLAN.md §8 ``validate``, §11, §7.3).

Validators never raise on bad content: they return ``Finding`` objects. Every code a
validator can emit is declared in ``CODES`` (with its severity) and documented in
``references/record-format.md`` — a test keeps the two in sync.

Three kinds of checks are registered:
- record checks   ``(ctx, loc) -> findings``    — per canonical record (optionally per prefix)
- artifact checks ``(ctx, rel, doc) -> findings`` — per artifact file
- workspace checks ``(ctx) -> findings``          — cross-file (duplicates, locks, …)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pflib import catalog, config, ids, records
from pflib.catalog import ArtifactSpec, RecordSchema
from pflib.records import Document, Record, RecordParseError

ERROR = "error"
WARN = "warn"

# code → (severity, meaning). Keep in sync with references/record-format.md.
CODES: dict[str, tuple[str, str]] = {
    "PARSE_ERROR": (ERROR, "Malformed record heading, field line, continuation or duplicate field"),
    "DUPLICATE_ID": (ERROR, "The same record ID is defined more than once"),
    "UNKNOWN_PREFIX": (ERROR, "A record's prefix is unknown or does not belong in this artifact"),
    "MISSING_FIELD": (ERROR, "A required field is absent"),
    "EMPTY_FIELD": (ERROR, "A required field is empty (and the schema does not allow it)"),
    "UNKNOWN_FIELD": (WARN, "A field that is not part of the record's schema"),
    "DANGLING_REF": (ERROR, "A reference to an ID that does not exist"),
    "WRONG_REF_TYPE": (ERROR, "A reference field cites a record of the wrong type"),
    "BAD_STATUS": (ERROR, "Status is not one of the allowed values (or rejected without Reason)"),
    "SUPERSEDED_TARGET_MISSING": (ERROR, "superseded-by targets a missing or other-type record"),
    "PROVISIONAL_ID_IN_CANONICAL": (ERROR, "A provisional ID (X-?n) appears in a canonical file"),
    "NEAR_DUPLICATE_TITLE": (WARN, "Two records of the same type have nearly identical titles"),
    "QUOTE_TOO_LONG": (ERROR, "A verbatim quote is longer than quotes.max_words"),
    "BAD_CONFIDENCE": (ERROR, "Confidence is not CONFIRMED, PROBABLE, INFERRED or UNKNOWN"),
    "CONFIDENCE_RULE": (ERROR, "The cited evidence does not support the stated confidence (§11)"),
    "PROVIDER_REPORT_AS_EVIDENCE": (ERROR, "A claim above INFERRED rests only on a skill's report"),
    "CONFLICT_ASYMMETRIC": (ERROR, "A conflict is declared on one side only"),
    "CONFLICT_UNRESOLVED": (WARN, "A conflicting pair has no unknown or Resolution explaining it"),
    "BAD_TIER": (ERROR, "Source tier is not an integer 1–5"),
    "BAD_CATEGORY": (ERROR, "Source category is not in the taxonomy"),
    "BAD_AUTHORITY": (ERROR, "Source authority is not High, Medium or Low"),
    "TIER_RAISED": (ERROR, "Tier is better than the category default (only lowering)"),
    "CANONICAL_URL_MISMATCH": (ERROR, "Canonical URL is not the canonical form of URL"),
    "DUPLICATE_SOURCE": (ERROR, "Two sources share a canonical URL"),
    "LOCK_VIOLATION": (ERROR, "A record of a closed stage was modified or lost references"),
    "LOCK_DELETED": (ERROR, "A record of a closed stage was deleted"),
}  # fmt: skip


@dataclass
class Finding:
    code: str
    severity: str
    artifact: str | None
    record_id: str | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "artifact": self.artifact,
            "record_id": self.record_id,
            "message": self.message,
        }


def finding(code: str, artifact: str | None, record_id: str | None, message: str) -> Finding:
    if code not in CODES:
        raise KeyError(f"undeclared finding code {code}")
    return Finding(code, CODES[code][0], artifact, record_id, message)


@dataclass
class Loc:
    """Where a canonical record lives."""

    rel: str
    spec: ArtifactSpec
    schema: RecordSchema | None  # None when the prefix does not belong in this artifact
    record: Record


@dataclass
class Context:
    ws: Path
    docs: dict[str, tuple[ArtifactSpec, Document]] = field(default_factory=dict)
    by_id: dict[str, list[Loc]] = field(default_factory=dict)
    parse_findings: list[Finding] = field(default_factory=list)
    max_quote_words: int = 25
    cache: dict[str, Any] = field(default_factory=dict)  # per-run derived indexes

    @classmethod
    def load(cls, ws: Path) -> Context:
        ctx = cls(ws=ws, max_quote_words=int(config.resolve("quotes.max_words", ws)))
        for spec in catalog.CATALOG:
            rels = (
                sorted(p.relative_to(ws).as_posix() for p in ws.glob(spec.path) if p.is_file())
                if spec.is_glob
                else ([spec.path] if (ws / spec.path).is_file() else [])
            )
            for rel in rels:
                errors: list[RecordParseError] = []
                text = (ws / rel).read_text(encoding="utf-8")
                doc = records.parse_document(text, path=rel, errors=errors)
                ctx.docs[rel] = (spec, doc)
                for err in errors:
                    ctx.parse_findings.append(finding(err.code, rel, None, err.message))
                for rec in doc.records:
                    parsed = ids.parse(rec.id, strict=False)
                    schema = spec.schema(parsed.prefix) if parsed else None
                    ctx.by_id.setdefault(rec.id, []).append(Loc(rel, spec, schema, rec))
        return ctx

    def get(self, record_id: str) -> Loc | None:
        locs = self.by_id.get(record_id)
        return locs[0] if locs else None

    def records(self, prefix: str | None = None) -> list[Loc]:
        out = [locs[0] for locs in self.by_id.values()]
        if prefix is not None:
            out = [loc for loc in out if loc.schema is not None and loc.schema.prefix == prefix]
        return sorted(out, key=lambda loc: (loc.rel, loc.record.start))


RecordCheck = Callable[[Context, Loc], list[Finding]]
ArtifactCheck = Callable[[Context, str, ArtifactSpec, Document], list[Finding]]
WorkspaceCheck = Callable[[Context], list[Finding]]

RECORD_CHECKS: list[tuple[str | None, RecordCheck]] = []
ARTIFACT_CHECKS: list[ArtifactCheck] = []
WORKSPACE_CHECKS: list[WorkspaceCheck] = []


def record_check(prefix: str | None = None) -> Callable[[RecordCheck], RecordCheck]:
    def deco(fn: RecordCheck) -> RecordCheck:
        RECORD_CHECKS.append((prefix, fn))
        return fn

    return deco


def artifact_check(fn: ArtifactCheck) -> ArtifactCheck:
    ARTIFACT_CHECKS.append(fn)
    return fn


def workspace_check(fn: WorkspaceCheck) -> WorkspaceCheck:
    WORKSPACE_CHECKS.append(fn)
    return fn


def owner_stage(f: Finding) -> str | None:
    """Stage that owns a finding: its record's schema owner, else its artifact's owner."""
    if f.record_id:
        parsed = ids.parse(f.record_id, strict=False)
        if parsed is not None:
            for spec in catalog.specs_for_prefix(parsed.prefix):
                return spec.owner_of(parsed.prefix)
    if f.artifact:
        artifact_spec = catalog.spec_for_path(f.artifact)
        if artifact_spec is not None:
            return artifact_spec.owner_stage
    return None


def run(ws: Path, stage: str | None = None, artifact: str | None = None) -> list[Finding]:
    """All findings for the workspace, optionally limited to one stage or artifact."""
    from pflib.validators import confidence_checks, generic, locks, ref_types, sources  # noqa: F401

    ctx = Context.load(ws)
    found: list[Finding] = list(ctx.parse_findings)
    for rel, (spec, doc) in sorted(ctx.docs.items()):
        for check in ARTIFACT_CHECKS:
            found.extend(check(ctx, rel, spec, doc))
    for locs in ctx.by_id.values():
        for loc in locs:
            for prefix, rcheck in RECORD_CHECKS:
                if loc.schema is not None and prefix in (None, loc.schema.prefix):
                    found.extend(rcheck(ctx, loc))
    for wcheck in WORKSPACE_CHECKS:
        found.extend(wcheck(ctx))
    if stage is not None:
        found = [f for f in found if owner_stage(f) == stage]
    if artifact is not None:
        found = [f for f in found if f.artifact == artifact]
    return sorted(found, key=lambda f: (f.artifact or "", f.record_id or "", f.code, f.message))


def summary(found: list[Finding]) -> dict[str, Any]:
    return {
        "errors": sum(f.severity == ERROR for f in found),
        "warnings": sum(f.severity == WARN for f in found),
        "findings": [f.to_dict() for f in found],
    }
