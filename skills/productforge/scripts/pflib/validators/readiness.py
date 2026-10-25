"""Build-readiness checks: once the architecture is being locked, no document that a build
session reads may leave a vendor, library, version or setting open."""

from __future__ import annotations

import re

from pflib import catalog, config, stages, state
from pflib.errors import PFError
from pflib.validators import Context, Finding, finding, workspace_check

_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def phrase_pattern(phrases: list[str]) -> re.Pattern[str] | None:
    """Whole-phrase, case-insensitive matcher for ``quality.undecided_phrases``."""
    parts = [re.escape(p.strip()) for p in phrases if p.strip()]
    if not parts:
        return None
    return re.compile(r"(?<!\w)(?:" + "|".join(parts) + r")(?!\w)", re.I)


_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_ALTERNATIVES_RE = re.compile(r"^\s*-\s+\**Alternatives\**\s*:", re.I)
_FIELD_RE = re.compile(r"^\s*-\s+\**[A-Z][A-Za-z ]*\**\s*:")


def _paragraphs(text: str) -> list[tuple[int, str]]:
    """``(first line number, text)`` per paragraph, skipping fenced code blocks and ADR
    ``- Alternatives:`` fields (rejected options legitimately say "not chosen")."""
    out: list[tuple[int, str]] = []
    block: list[str] = []
    start = 0
    fenced = False
    skipping = False  # inside an Alternatives field

    def flush() -> None:
        if block:
            out.append((start, " ".join(block)))
            block.clear()

    for n, line in enumerate(text.splitlines(), start=1):
        if _FENCE_RE.match(line):
            flush()
            fenced = not fenced
            continue
        if fenced:
            continue
        if not line.strip():
            flush()
            skipping = False
            continue
        if _ALTERNATIVES_RE.match(line):
            flush()
            skipping = True
            continue
        if skipping:
            if _FIELD_RE.match(line):
                skipping = False  # the next ADR field ends it
            else:
                continue
        if not block:
            start = n
        block.append(line.strip())
    flush()
    return out


def undecided_hits(text: str, pattern: re.Pattern[str]) -> list[tuple[int, str]]:
    """(line number, phrase) per match outside HTML comments, fenced code and Alternatives
    fields. Matching is per paragraph with whitespace normalised, so a phrase split across
    lines is caught; the line is the paragraph's first."""
    text = _COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return [
        (n, re.sub(r"\s+", " ", m.group(0)))
        for n, para in _paragraphs(text)
        for m in pattern.finditer(para)
    ]


def _active(ctx: Context) -> bool:
    """ARCHITECTURE_LOCKED or a later stage is the current stage."""
    try:
        current = state.load(ctx.ws).state.value
    except PFError:
        return False
    return stages.ORDER.index(current) >= stages.ORDER.index(stages.ARCHITECTURE_LOCKED)


@workspace_check
def undecided_choices(ctx: Context) -> list[Finding]:
    if not _active(ctx):
        return []
    pattern = phrase_pattern(list(config.resolve("quality.undecided_phrases", ctx.ws)))
    if pattern is None:
        return []
    out: list[Finding] = []
    for rel, (spec, _doc) in sorted(ctx.docs.items()):
        if rel == catalog.TRACEABILITY_PATH:
            continue  # a generated view, not a build document
        if stages.ORDER.index(spec.owner_stage) < stages.ORDER.index(stages.ARCHITECTURE_LOCKED):
            continue
        hits = undecided_hits((ctx.ws / rel).read_text(encoding="utf-8"), pattern)
        if hits:
            shown = "; ".join(f"line {n}: {phrase!r}" for n, phrase in hits[:5])
            more = f" (+{len(hits) - 5} more)" if len(hits) > 5 else ""
            msg = f"{rel} leaves a choice open — {shown}{more}; decide it and name it"
            out.append(finding("UNDECIDED_CHOICE", rel, None, msg))
    return out
