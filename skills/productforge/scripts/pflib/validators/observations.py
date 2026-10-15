"""Observation checks: OB kinds are a closed set, an observation
rests on an observed-session source, and its local artifact exists unless the session was
discarded (raw sessions are local only, so a missing file is a warning, not an error).

Observations show **behaviour**, never internals: an observed session is Tier 1, so without this
rule "uses ClickHouse — OB-012" would satisfy the Tier ≤ 2 bar for a target's internals.
When a claim's — or an inference's Target implementation's — only Tier ≤ 2 support is observed
sessions, every technology it names must appear in the cited observations themselves (a
``/graphql`` endpoint, a WebSocket channel): ``INTERNALS_FROM_OBSERVATION``."""

from __future__ import annotations

from pflib import records, tech_terms, workspace
from pflib.validators import Context, Finding, Loc, finding, record_check
from pflib.validators.confidence_checks import source_index

KINDS = ("screen", "action", "endpoint", "realtime", "permission", "error")
DISCARDED = "discarded"
OBSERVED = "observed-session"


def _discarded_sessions(ctx: Context) -> set[str]:
    if "observe_discarded" not in ctx.cache:
        ctx.cache["observe_discarded"] = {
            str(h.get("session")) for h in workspace.read_history(ctx.ws)
            if h.get("event") == "observe-discard"
        }  # fmt: skip
    found: set[str] = ctx.cache["observe_discarded"]
    return found


@record_check("OB")
def observation(ctx: Context, loc: Loc) -> list[Finding]:
    rec, out = loc.record, []
    if not records.is_active(rec):
        return []
    kind = rec.get("Kind").strip()
    if kind not in KINDS:
        msg = f"{rec.id}: Kind {kind!r} is not one of {', '.join(KINDS)}"
        out.append(finding("OB_KIND_UNKNOWN", loc.rel, rec.id, msg))
    for ref in records.parse_refs(rec.get("Evidence")):
        src = ctx.get(ref)
        if src is not None and src.record.get("Category").strip() != "observed-session":
            out.append(finding("OB_NOT_FROM_SESSION", loc.rel, rec.id,
                               f"{rec.id}: {ref} is not an observed-session source; observations "
                               "come only from `pf.py observe ingest`"))  # fmt: skip
    artifact = rec.get("Artifact").strip().strip("`")
    if artifact and artifact != DISCARDED and not (ctx.ws / artifact).exists():
        parts = artifact.split("/")
        session = parts[2] if len(parts) > 2 and parts[:2] == [".productforge", "observe"] else ""
        if session not in _discarded_sessions(ctx):
            out.append(finding("OB_ARTIFACT_MISSING", loc.rel, rec.id,
                               f"{rec.id}: {artifact} is not on this computer (raw sessions are "
                               "local only and never committed)"))  # fmt: skip
    return out


def _observed_only(ctx: Context, refs: list[str]) -> tuple[bool, str]:
    """(True when every Tier ≤ 2 source behind ``refs`` is an observed session — and there is
    one, the text of the observations reached on the way)."""
    index = source_index(ctx)
    strong = [s for ref in refs for s in index.effective_sources_of(ref)
              if s.tier is not None and s.tier <= 2]  # fmt: skip
    if not strong or any(s.category != OBSERVED for s in strong):
        return False, ""
    texts, stack, seen = [], list(refs), set()
    while stack:
        ref = stack.pop()
        loc = ctx.get(ref)
        if ref in seen or loc is None:
            continue
        seen.add(ref)
        if ref.startswith("OB-"):
            texts += [loc.record.title, loc.record.get("Detail")]
        elif not ref.startswith("S-"):
            stack.extend(records.parse_refs(loc.record.get("Evidence")))
    return True, "\n".join(texts)


def _unobserved_terms(text: str, observed: str) -> list[str]:
    seen = {t.lower() for t in tech_terms.find(observed)}
    return sorted({t for t in tech_terms.find(text) if t.lower() not in seen})


@record_check("D")
def claim_internals(ctx: Context, loc: Loc) -> list[Finding]:
    rec = loc.record
    refs = records.parse_refs(rec.get("Evidence"))
    if not records.is_active(rec) or not any(r.startswith("OB-") for r in refs):
        return []
    only, observed = _observed_only(ctx, refs)
    terms = _unobserved_terms(rec.get("Claim"), observed) if only else []
    if not terms:
        return []
    msg = (f"{rec.id}: names {', '.join(terms)} on observed-session evidence alone; an observation "
           "shows behaviour, not how the product is built — cite a source that states it, or "
           "describe the behaviour")  # fmt: skip
    return [finding("INTERNALS_FROM_OBSERVATION", loc.rel, rec.id, msg)]


@record_check("A")
def inference_internals(ctx: Context, loc: Loc) -> list[Finding]:
    from pflib.validators.inference import is_unknown, qualifying_claims

    rec = loc.record
    target = rec.get("Target implementation")
    if not records.is_active(rec) or not target.strip() or is_unknown(target):
        return []
    claims = qualifying_claims(ctx, rec)
    if not claims:
        return []  # TARGET_IMPL_UNSUPPORTED covers it
    only, observed = _observed_only(ctx, claims)
    terms = _unobserved_terms(target, observed) if only else []
    if not terms:
        return []
    msg = (f"{rec.id}: Target implementation names {', '.join(terms)}, but its qualifying claims "
           "rest only on observed sessions; observed API shapes may be stated, internals stay "
           "UNKNOWN")  # fmt: skip
    return [finding("INTERNALS_FROM_OBSERVATION", loc.rel, rec.id, msg)]
