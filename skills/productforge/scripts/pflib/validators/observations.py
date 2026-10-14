"""Observation checks (IMPLEMENTATION_PLAN.md §23.3): OB kinds are a closed set, an observation
rests on an observed-session source, and its local artifact exists unless the session was
discarded (raw sessions are local only, so a missing file is a warning, not an error)."""

from __future__ import annotations

from pflib import records, workspace
from pflib.validators import Context, Finding, Loc, finding, record_check

KINDS = ("screen", "action", "endpoint", "realtime", "permission", "error")
DISCARDED = "discarded"


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
