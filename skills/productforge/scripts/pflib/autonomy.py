"""Autonomous mode: a recorded, revocable, per-workspace consent and the decisions log.

With an active grant, ``advance --auto`` and ``complete --auto`` work without a per-transition
confirmation (the gate still decides), and the skill picks the recommended option at every
question, logging each choice with ``pf.py decide``. Without a grant nothing changes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pflib import config, state, workspace
from pflib.errors import UsageError

CONSENT_TEXT = (
    "Autonomous mode lets ProductForge run this workspace without asking you again. While the "
    "grant stands it advances every stage whose exit gate passes, one stage per step; it chooses "
    "the option marked Recommended at every question (the domain split, the scope, the "
    "architecture and the plan) and logs each choice in .productforge/decisions.jsonl; it declines "
    "every capability install and uses the built-in providers; it researches competitors; it "
    "skips observe mode, which needs you; it runs subagents in parallel batches up to the "
    "configured maximum; and it writes nothing outside the workspace. The driver (`pf.py auto`) "
    "also starts headless Claude sessions with the permission arguments from the configuration. "
    "Gates still decide every transition. You can read the decisions with `pf.py decide --list` "
    "and end autonomy at any time with `pf.py autonomy revoke`."
)


def text_hash(text: str | None = None) -> str:
    return hashlib.sha256((CONSENT_TEXT if text is None else text).encode("utf-8")).hexdigest()


def text(ws: Path | None) -> str:
    """The consent text for this workspace: the shipped text plus the effective driver settings
    (the ``claude`` binary and the permission arguments), so changing either changes the hash."""
    args = " ".join(str(a) for a in config.resolve("auto.permission_args", ws))
    binary = config.resolve("capabilities.claude_bin", ws)
    return (
        f"{CONSENT_TEXT}\n\nEffective settings for this workspace: the driver runs `{binary}` "
        f"with the permission arguments: {args or '(none)'}."
    )


def current_hash(ws: Path | None) -> str:
    return text_hash(text(ws))


def grant(st: state.WorkspaceState, now: str, ws: Path) -> None:
    st.autonomy = {"granted_at": now, "text_sha256": current_hash(ws)}


def revoke(st: state.WorkspaceState) -> bool:
    """Remove the grant; returns whether there was one (nothing changes when there was none)."""
    if not st.autonomy:
        return False
    st.autonomy = {}
    return True


def active(st: state.WorkspaceState, ws: Path) -> bool:
    """A grant counts only while it names the consent text currently rendered for ``ws``."""
    return bool(st.autonomy) and st.autonomy.get("text_sha256") == current_hash(ws)


def status(st: state.WorkspaceState, ws: Path) -> dict[str, Any]:
    return {"active": active(st, ws), "granted_at": st.autonomy.get("granted_at")}


def require_active(st: state.WorkspaceState, ws: Path) -> None:
    if not active(st, ws):
        raise UsageError(
            "autonomy is not granted for this workspace (pf.py autonomy show, then grant "
            "--confirmed --text-sha256 <hash>)",
            code="AUTONOMY_NOT_GRANTED",
        )


def show(st: state.WorkspaceState, ws: Path) -> dict[str, Any]:
    return {**status(st, ws), "text": text(ws), "text_sha256": current_hash(ws)}


def do_grant(ws: Path, confirmed: bool, text_sha256: str | None) -> dict[str, Any]:
    if not confirmed:
        raise UsageError(
            "nothing recorded: show the consent text (pf.py autonomy show), ask the user, then "
            "re-run with --confirmed --text-sha256 <hash>",
            code="AUTONOMY_NOT_CONFIRMED",
        )
    if not text_sha256:
        raise UsageError("grant needs --text-sha256 from `autonomy show`", code="USAGE_ERROR")
    if text_sha256 != current_hash(ws):
        raise UsageError(
            "the consent text changed since it was shown; run `autonomy show` again",
            code="AUTONOMY_TEXT_CHANGED",
        )
    st = state.load(ws)
    grant(st, workspace.iso(workspace.utc_now()), ws)
    state.save(ws, st)
    workspace.append_history(ws, {"event": "autonomy-grant", "text_sha256": current_hash(ws)})
    return show(st, ws)


def do_revoke(ws: Path) -> dict[str, Any]:
    st = state.load(ws)
    if revoke(st):
        state.save(ws, st)
        workspace.append_history(ws, {"event": "autonomy-revoke"})
    return show(st, ws)


# -- decisions log -------------------------------------------------------------------------------
def decisions_path(ws: Path) -> Path:
    return workspace.pf_dir(ws) / workspace.DECISIONS


def read_decisions(ws: Path) -> list[dict[str, Any]]:
    path = decisions_path(ws)
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue  # a torn or hand-edited line never breaks status or the driver
        if isinstance(row, dict):
            rows.append(row)
    return rows


def count_decisions(ws: Path) -> int:
    return len(read_decisions(ws))


def decide(
    ws: Path, question: str, choice: str, why: str, command: str | None = None
) -> dict[str, Any]:
    fields = {"question": question, "choice": choice, "why": why}
    for name, value in fields.items():
        if not value.strip():
            raise UsageError(f"decide needs a non-empty --{name}", code="USAGE_ERROR")
    st = state.load(ws)
    entry: dict[str, Any] = {
        "ts": workspace.iso(workspace.utc_now()),
        "stage": st.state.value,
        **({"command": command} if command else {}),
        **{k: v.strip() for k, v in fields.items()},
        "autonomy_active": active(st, ws),
    }
    with open(decisions_path(ws), "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"recorded": entry, "decisions": count_decisions(ws)}
