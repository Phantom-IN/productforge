"""Generated regions must equal a fresh render (they are views over records)."""

from __future__ import annotations

from pflib import render
from pflib.catalog import ArtifactSpec
from pflib.index import WorkspaceIndex
from pflib.records import Document
from pflib.validators import Context, Finding, artifact_check, finding


@artifact_check
def generated_regions(ctx: Context, rel: str, spec: ArtifactSpec, doc: Document) -> list[Finding]:
    renderer = render.RENDERERS.get(rel)
    if renderer is None:
        return []
    if "render_index" not in ctx.cache:
        ctx.cache["render_index"] = WorkspaceIndex(ctx.ws)
    expected = renderer.regions(ctx.cache["render_index"])
    out: list[Finding] = []
    for name, body in render.regions(doc.text).items():
        if name in expected and expected[name] and body != expected[name]:
            out.append(finding("GENERATED_REGION_EDITED", rel, None,
                               f"{rel}: generated region '{name}' differs from the records — it "
                               "was hand-edited or is stale; run `pf.py render`"))  # fmt: skip
    return out
