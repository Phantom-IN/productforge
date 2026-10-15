#!/usr/bin/env python3.11
"""ProductForge stage guard — a PreToolUse hook for Write, Edit, MultiEdit and NotebookEdit.

Inside a ProductForge workspace (a directory with ``.productforge/state.json``) it blocks writes
that would bypass the lifecycle:

- canonical record files (``research/sources.md``, ``spec/PRODUCT_SPEC.md``, ADR files …) — only
  ``pf.py merge`` writes them; agents write their staging folder;
- artifacts owned by a stage other than the open one (closed stages are append-only through merge;
  later stages are not open yet);
- generated views (``spec/TRACEABILITY.md``) and ``.productforge/`` itself, except staging.

Everything else is allowed — staging, the open stage's documents, and the code the generated
project builds. Outside a workspace the hook does nothing. Any internal error **fails open**
(allow + a note on stderr) so a bug can never brick a session. Stdlib only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

GUARDED_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
STATE = (".productforge", "state.json")


def _find_workspace(path: Path) -> Path | None:
    for parent in [path, *path.parents]:
        if parent.joinpath(*STATE).is_file():
            return parent
    return None


def _deny(reason: str) -> dict[str, object]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"ProductForge stage guard: {reason}",
        }
    }


def decide(payload: dict[str, object]) -> dict[str, object] | None:
    """The hook's decision for one PreToolUse payload (None = allow, say nothing)."""
    if payload.get("tool_name") not in GUARDED_TOOLS:
        return None
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return None
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not raw:
        return None
    path = Path(str(raw))
    if not path.is_absolute():
        path = Path(str(payload.get("cwd") or ".")) / path
    path = path.resolve()
    ws = _find_workspace(path.parent)
    if ws is None:
        return None  # not a ProductForge workspace: ordinary work is never affected
    rel = path.relative_to(ws).as_posix()

    if rel.startswith(".productforge/staging/"):
        return None
    if rel.startswith(".productforge/observe/"):
        return _deny(
            f"{rel} is an observe-mode session; only the recorder and `pf.py observe` write it "
            "(`pf.py observe discard <session> --reason …` deletes it)."
        )
    if rel.startswith(".productforge/"):
        return _deny(f"{rel} is ProductForge's own state; only `pf.py` changes it.")

    scripts = Path(__file__).resolve().parent.parent / "skills" / "productforge" / "scripts"
    sys.path.insert(0, str(scripts))
    from pflib import catalog, render

    spec = catalog.spec_for_path(rel)
    if spec is None:
        return None  # not a ProductForge artifact (e.g. the generated project's code)
    state = json.loads(ws.joinpath(*STATE).read_text(encoding="utf-8"))
    open_stage = str(state.get("state", ""))
    if spec.kind != catalog.KIND_DOCUMENT:
        return _deny(
            f"{rel} holds records; stage changes in `.productforge/staging/<run>/` and apply them "
            "with `pf.py merge <run-id>` (`/productforge` does this for you)."
        )
    if rel in render.RENDERERS and not spec.schemas:
        return _deny(f"{rel} is generated; rebuild it with `pf.py trace --write` / `pf.py render`.")
    if spec.owner_stage != open_stage:
        return _deny(
            f"{rel} belongs to {spec.owner_stage}, but the open stage is {open_stage}. "
            f'Use `pf.py reopen {spec.owner_stage} --reason "…"` to change it.'
        )
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        decision = decide(payload) if isinstance(payload, dict) else None
    except Exception as exc:  # noqa: BLE001 — fail open, never block a session on a guard bug
        print(f"productforge stage guard: allowing after internal error: {exc}", file=sys.stderr)
        return 0
    if decision is not None:
        print(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
