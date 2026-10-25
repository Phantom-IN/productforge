"""Recorded waivers: a gate requirement the user explicitly chose to skip, with the reason.

Waivers live in ``state.json`` under ``waivers: {<name>: {reason, at}}`` and are logged to the
history. Only the competitor signal can be waived, and only while DISCOVERY, PRODUCT_MODEL or
SCOPE_DEFINED is the open stage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pflib import state, workspace
from pflib.errors import UsageError

COMPETITORS = "competitors"
WAIVABLE = (COMPETITORS,)
OPEN_STAGES = (state.State.DISCOVERY, state.State.PRODUCT_MODEL, state.State.SCOPE_DEFINED)


def get(ws: Path, name: str) -> dict[str, str] | None:
    """The recorded waiver (``{reason, at}``) or None."""
    waiver = state.load(ws).waivers.get(name)
    return waiver if isinstance(waiver, dict) else None


def waive(ws: Path, name: str, reason: str, revoke: bool = False) -> dict[str, Any]:
    if name not in WAIVABLE:
        raise UsageError(f"cannot waive {name!r} (waivable: {', '.join(WAIVABLE)})",
                         code="UNKNOWN_WAIVER")  # fmt: skip
    st = state.load(ws)
    if st.state not in OPEN_STAGES:
        raise UsageError(
            f"{name} can only be waived while DISCOVERY, PRODUCT_MODEL or SCOPE_DEFINED is open "
            f"(open stage is {st.state.value})",
            code="WAIVER_STAGE_CLOSED",
        )
    if revoke:
        had = st.waivers.pop(name, None) is not None
        state.save(ws, st)
        workspace.append_history(ws, {"event": "waive-revoke", "waiver": name})
        return {"waived": False, "reason": None, "revoked": had}
    if not reason.strip():
        raise UsageError("a waiver needs a non-empty --reason", code="WAIVER_NEEDS_REASON")
    st.waivers[name] = {"reason": reason.strip(), "at": workspace.iso(workspace.utc_now())}
    state.save(ws, st)
    workspace.append_history(ws, {"event": "waive", "waiver": name, "reason": reason.strip()})
    return {"waived": True, "reason": reason.strip()}
