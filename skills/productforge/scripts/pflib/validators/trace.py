"""Traceability checks (IMPLEMENTATION_PLAN.md §17), once phase files exist."""

from __future__ import annotations

from pflib import plans, trace
from pflib.validators import Context, Finding, finding, workspace_check


@workspace_check
def traceability(ctx: Context) -> list[Finding]:
    if not plans.phase_files(ctx.ws):
        return []
    return [finding(g.code, g.rel, g.record_id, g.message) for g in trace.gaps(ctx.ws)]
