"""Architecture checks (IMPLEMENTATION_PLAN.md §15): decisions with alternatives, every requirement
and inference addressed, a complete stack, an enforced invariant set and a concrete repository."""

from __future__ import annotations

from pflib import architecture, catalog, records
from pflib.validators import Context, Finding, Loc, finding, record_check, workspace_check

ARCH = catalog.ARCHITECTURE_PATH


def _sample(ids: list[str], limit: int = 10) -> str:
    return ", ".join(ids[:limit]) + (" …" if len(ids) > limit else "")


@record_check("ADR")
def adr_alternatives(ctx: Context, loc: Loc) -> list[Finding]:
    rec = loc.record
    if not records.is_active(rec) or len(architecture.alternatives(rec.get("Alternatives"))) >= 2:
        return []
    msg = f"{rec.id} lists fewer than two alternatives (separate them with ';')"
    return [finding("ADR_NO_ALTERNATIVES", loc.rel, rec.id, msg)]


@record_check("ADR")
def adr_deviation(ctx: Context, loc: Loc) -> list[Finding]:
    rec = loc.record
    if not records.is_active(rec):
        return []
    reqs = [r for r in records.parse_refs(rec.get("Deviates from"))
            if (r_loc := ctx.get(r)) is not None and records.is_active(r_loc.record)]  # fmt: skip
    if not reqs:
        return []
    msg = (f"{rec.id} deviates from {', '.join(reqs)}; keep the spec consistent with "
           '`pf.py reopen SCOPE_DEFINED --reason "…"` and amend the requirement, or accept the '
           "deviation knowingly")  # fmt: skip
    return [finding("ADR_DEVIATES_FROM_REQUIREMENT", loc.rel, rec.id, msg)]


@record_check("INV")
def invariant_enforced(ctx: Context, loc: Loc) -> list[Finding]:
    rec = loc.record
    if architecture.enforcement_kind(rec.get("Enforced by")) is not None:
        return []
    msg = (f"{rec.id}: 'Enforced by' must start with one of "
           f"{', '.join(architecture.ENFORCEMENT)} (then the mechanism)")  # fmt: skip
    return [finding("INVARIANT_UNENFORCED", loc.rel, rec.id, msg)]


@record_check("AP")
def proposal_decision_is_current(ctx: Context, loc: Loc) -> list[Finding]:
    stale = [ref for ref in records.parse_refs(loc.record.get("Decision"))
             if (d := ctx.get(ref)) is not None and not records.is_active(d.record)]  # fmt: skip
    if not stale:
        return []
    msg = (f"{loc.record.id} cites superseded {', '.join(stale)}; amend its Decision "
           "(### AMEND with Decision and Why)")  # fmt: skip
    return [finding("SUPERSEDED_DECISION_CITED", loc.rel, loc.record.id, msg)]


@workspace_check
def architecture_document(ctx: Context) -> list[Finding]:
    text = architecture.text_of(ctx.ws)
    if text is None:
        return []  # design has not started (ARCHITECTURE_LOCKED)
    out: list[Finding] = []
    if architecture.DISCLAIMER not in text:
        msg = f"{ARCH} must state '{architecture.DISCLAIMER} <target>' in its preamble"
        out.append(finding("ARCHITECTURE_DISCLAIMER_MISSING", ARCH, None, msg))
    rows = architecture.stack_rows(text)
    bad = [r[0] for r in rows if len(r) < 2 or architecture.INCOMPLETE_RE.match(r[1])]
    if not rows or bad:
        msg = (f"## Stack has open choices: {', '.join(bad)}" if bad
               else "## Stack has no `| Concern | Choice | ADR |` table")  # fmt: skip
        out.append(finding("STACK_INCOMPLETE", ARCH, None, msg))
    _, error = architecture.tree(text)
    if error:
        out.append(finding("BAD_REPO_TREE", ARCH, None, f"## Repository structure: {error}"))
    for line in architecture.section(text, "Components").splitlines():
        if line.startswith("- ") and not architecture.JUSTIFY_RE.search(line):
            msg = f"component {line[2:].split(':')[0].strip()!r} cites no R, A or ADR"
            out.append(finding("UNJUSTIFIED_COMPONENT", ARCH, None, msg))
    cov = architecture.coverage(ctx.ws)
    if cov.unaddressed:
        msg = (f"requirements no ADR satisfies and no convention covers: "
               f"{_sample(cov.unaddressed)}")  # fmt: skip
        out.append(finding("REQUIREMENT_UNADDRESSED", ARCH, None, msg))
    if cov.unproposed or cov.multi_proposed:
        parts = [f"no proposal: {_sample(cov.unproposed)}"] if cov.unproposed else []
        parts += [f"several proposals: {_sample(cov.multi_proposed)}"] if cov.multi_proposed else []
        msg = "architecture inferences need exactly one AP proposal — " + "; ".join(parts)
        out.append(finding("INFERENCE_UNPROPOSED", ARCH, None, msg))
    if cov.topics_missing:
        msg = (f"mandatory topics with neither an ADR (Topic) nor a line under "
               f"## Not applicable topics: {', '.join(cov.topics_missing)}")  # fmt: skip
        out.append(finding("ADR_TOPIC_MISSING", ARCH, None, msg))
    return out
