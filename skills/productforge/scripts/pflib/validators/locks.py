"""Closed-stage lock checks.

Allowed after a stage closes: new records, and *added* references in union fields (merge's
dedupe union). Anything else — a changed field or title, a removed reference, a deleted
record — is a violation.
"""

from __future__ import annotations

from pflib import catalog, ids, state
from pflib.errors import PFError
from pflib.validators import Context, Finding, finding, workspace_check


@workspace_check
def locked_records(ctx: Context) -> list[Finding]:
    try:
        st = state.load(ctx.ws)
    except PFError:
        return []  # reported by the G-STATE-FILE-VALID gate condition
    out: list[Finding] = []
    for stage, snapshot in sorted(st.locks.items()):
        for record_id, locked in sorted(snapshot.items()):
            loc = ctx.get(record_id)
            parsed = ids.parse(record_id, strict=False)
            spec = catalog.specs_for_prefix(parsed.prefix)[0] if parsed else None
            artifact = loc.rel if loc else (spec.path if spec else None)
            if loc is None or loc.schema is None:
                out.append(
                    finding(
                        "LOCK_DELETED",
                        artifact,
                        record_id,
                        f"{record_id} belongs to closed stage {stage} and was deleted; "
                        f"supersede records instead of deleting them",
                    )
                )
                continue
            now = state.record_lock(loc.record, loc.schema)
            removed = sorted(set(locked.get("refs", [])) - set(now["refs"]))
            if now["hash"] != locked.get("hash") or removed:
                what = f"references removed: {', '.join(removed)}" if removed else "fields changed"
                out.append(
                    finding(
                        "LOCK_VIOLATION",
                        artifact,
                        record_id,
                        f"{record_id} belongs to closed stage {stage} ({what}); use "
                        f"`pf.py reopen {stage}` to change it",
                    )
                )
    return out
