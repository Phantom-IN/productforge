"""Phase-plan checks — the phase lint as validator findings."""

from __future__ import annotations

from pflib import plans
from pflib.validators import Context, Finding, finding, workspace_check


@workspace_check
def phase_plan(ctx: Context) -> list[Finding]:
    issues = plans.lint(ctx.ws).issues + plans.root_doc_issues(ctx.ws)
    return [finding(i.code, i.rel, None, i.message) for i in issues]
