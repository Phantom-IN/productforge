"""A short blueprint summary (``report.publish``).

Composed only from script output — counts, the funnel, decision counts, ADR titles and the phase
list — so it can be shared without exposing research content. The orchestrator publishes it
through the ``report.publish`` capability **only when the user asks**.
"""

from __future__ import annotations

from pathlib import Path

from pflib import metrics, plans, records, score, state
from pflib.index import WorkspaceIndex


def markdown(ws: Path) -> str:
    st = state.load(ws)
    index = WorkspaceIndex(ws)
    s = metrics.summary(ws, index)
    funnel = metrics.funnel(ws, index)
    counts = score.report(ws)["counts"]
    adrs = sorted((a for _, a in index.records("ADR") if records.is_active(a)), key=lambda a: a.id)
    phases = plans.lint(ws).summary()
    name, target = st.product.get("our_name", ""), st.product.get("name", "")
    lines = [
        f"# {name} — blueprint summary",
        "",
        f"An independent product informed by public research of {target}. Stage: {st.state.value}.",
        "",
        "## Research",
        "",
        f"{s['sources']} sources · {s['claims']} claims · {s['unknowns']} unknowns · "
        f"{s['features']} features in {s['domains']} domains · {s['workflows']} workflows · "
        f"{s['entities']} entities · {s['roles']} roles · {s['integrations']} integrations",
        "",
        "## Reduction funnel",
        "",
        f"{funnel['observed_claims']} observed claims → {funnel['features']} features → "
        f"{funnel['core_requirements']} core requirements → {funnel['v1_capabilities']} V1 "
        f"capabilities → {funnel['phases'] if funnel['phases'] is not None else '—'} phases",
        "",
        "## Scope decisions",
        "",
        " · ".join(f"{k}: {v}" for k, v in counts.items()),
    ]
    if adrs:
        lines += ["", "## Architecture decisions", ""]
        lines += [f"- {a.id} — {a.title}" for a in adrs]
    if phases:
        lines += ["", "## Phases", ""]
        lines += [f"- {p['number']} — {p['name']}" for p in phases]
    return "\n".join(lines) + "\n"
