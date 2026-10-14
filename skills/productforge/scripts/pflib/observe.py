"""Observe mode (IMPLEMENTATION_PLAN.md §23): consent now; sessions, summaries and ingestion in
later v2 phases.

The user drives the real product in a browser ProductForge controls; ProductForge records what the
product does. Consent is asked once per workspace and recorded with a hash of the exact text the
user saw — a changed text asks again.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pflib import state, workspace
from pflib.errors import UsageError

CONSENT_TEXT = (
    "Observe mode opens the product in a browser window that ProductForge controls. You sign in "
    "with your own account and use the product yourself; ProductForge never clicks for you. While "
    "recording it saves, on this computer only: the pages and screens you visit, what you click "
    "(not what you type), screenshots (unless you turn them off) and the shape of the product's "
    "network traffic. Passwords, payment fields, cookies and tokens are never stored, and nothing "
    "raw is merged into the spec or committed. The product's terms of service may forbid reverse "
    "engineering or automated access — whether to use observe mode on it is your decision. You "
    "can pause or stop at any time and delete a session with `pf.py observe discard`."
)


def consent_hash(text: str | None = None) -> str:
    return hashlib.sha256((CONSENT_TEXT if text is None else text).encode("utf-8")).hexdigest()


def consent_status(st: state.WorkspaceState) -> dict[str, Any]:
    given = st.observe_consent or {}
    current = given.get("text_sha256") == consent_hash()
    return {"consented": bool(given) and current, "at": given.get("at"), "stale": bool(given)
            and not current, "text": CONSENT_TEXT}  # fmt: skip


def record_consent(ws: Path, confirmed: bool) -> dict[str, Any]:
    st = state.load(ws)
    if not confirmed:
        out = consent_status(st)
        out["message"] = (
            "nothing recorded: show the text, ask the user, then re-run with --confirmed"
        )
        return out
    now = workspace.iso(workspace.utc_now())
    st.observe_consent = {"at": now, "text_sha256": consent_hash()}
    state.save(ws, st)
    workspace.append_history(ws, {"event": "observe-consent", "text_sha256": consent_hash()})
    return consent_status(st)


def require_consent(ws: Path) -> None:
    if not consent_status(state.load(ws))["consented"]:
        raise UsageError("observe mode needs the user's consent first (pf.py observe consent)",
                         code="OBSERVE_NO_CONSENT")  # fmt: skip
