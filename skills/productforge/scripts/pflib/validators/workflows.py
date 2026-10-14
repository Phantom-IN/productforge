"""Workflow-file checks (IMPLEMENTATION_PLAN.md §12.3): tagged steps, evidence, confidence."""

from __future__ import annotations

from pflib import ids, workflows
from pflib.catalog import KIND_RECORD_FILE, ArtifactSpec
from pflib.records import Document
from pflib.validators import Context, Finding, artifact_check, finding
from pflib.validators.confidence_checks import source_index

STEP_EVIDENCE = ("S-", "D-", "OB-")  # an [observed] step cites a source, claim or observation

CONFIRMED_OBSERVED_SHARE = 0.5  # a CONFIRMED workflow: ≥ half its observed steps on Tier ≤ 2


@artifact_check
def workflow_steps(ctx: Context, rel: str, spec: ArtifactSpec, doc: Document) -> list[Finding]:
    if spec.kind != KIND_RECORD_FILE or spec.schema("W") is None or not doc.records:
        return []
    rec = doc.records[0]
    steps, bad = workflows.parse_steps(doc.text)
    out: list[Finding] = []
    for line in bad:
        out.append(finding("BAD_STEP_TAG", rel, rec.id,
                           f"{rec.id}: step {line!r} needs '[observed]' or '[implied-system]' "
                           "after its number"))  # fmt: skip
    if not steps:
        if not bad:
            out.append(finding("BAD_STEPS", rel, rec.id, f"{rec.id} has no numbered ## Steps"))
        return out
    numbers = [s.number for s in steps]
    if numbers != list(range(1, len(steps) + 1)) and not bad:
        msg = f"{rec.id}: steps must be numbered 1..{len(steps)} (got {numbers})"
        out.append(finding("BAD_STEPS", rel, rec.id, msg))
    for step in steps:
        for ref in step.refs:
            if not ids.is_provisional(ref) and ctx.get(ref) is None:
                out.append(finding("DANGLING_REF", rel, rec.id,
                                   f"{rec.id} step {step.number} cites missing {ref}"))  # fmt: skip
        if step.tag == "observed" and not any(r.startswith(STEP_EVIDENCE) for r in step.refs):
            out.append(finding("OBSERVED_STEP_NO_EVIDENCE", rel, rec.id,
                               f"{rec.id} step {step.number} is [observed] but cites no S-/D-/OB- "
                               "evidence; cite it or mark it [implied-system]"))  # fmt: skip
    implied = [s for s in steps if s.tag == "implied-system"]
    explained = "none" in (doc.section_text("Engineering requirements surfaced") or "").lower()
    if not implied and not explained:
        out.append(finding("NO_SYSTEM_STEPS", rel, rec.id,
                           f"{rec.id} has no [implied-system] steps; most flows persist, authorize "
                           "or notify — add them, or write 'none' under Engineering requirements "
                           "surfaced"))  # fmt: skip
    if rec.get("Confidence").strip() == "CONFIRMED":
        index = source_index(ctx)
        observed = [s for s in steps if s.tag == "observed"]
        strong = 0
        for step in observed:
            tiers = [
                src.tier
                for ref in step.refs
                for src in index.effective_sources_of(ref)
                if src.tier is not None
            ]
            if tiers and min(tiers) <= 2:
                strong += 1
        if not observed or strong / len(observed) < CONFIRMED_OBSERVED_SHARE:
            out.append(finding("WORKFLOW_CONFIDENCE", rel, rec.id,
                               f"{rec.id} is CONFIRMED but only {strong} of {len(observed)} "
                               "observed steps rest on Tier ≤ 2 evidence; use PROBABLE or cite "
                               "stronger sources"))  # fmt: skip
    return out
