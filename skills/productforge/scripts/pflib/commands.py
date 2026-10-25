"""Which ``/productforge`` command may run now?

Verdicts:
- ``allowed``          — the command belongs to the open stage.
- ``needs_transition`` — it belongs to the next stage; show the gate report, ask the user,
  then ``pf.py advance --to <stage> --confirmed``. Never more than one stage per command.
- ``refused``          — it belongs to a later stage (finish the missing stages first) or to
  a closed earlier stage (use ``reopen``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pflib import competitors, config, gates, state, waivers
from pflib.errors import UsageError
from pflib.index import WorkspaceIndex
from pflib.state import State

COMMAND_STAGE: dict[str, State] = {
    "research": State.DISCOVERY,
    "features": State.PRODUCT_MODEL,
    "workflows": State.PRODUCT_MODEL,
    "model": State.PRODUCT_MODEL,
    "competitors": State.PRODUCT_MODEL,
    "scope": State.SCOPE_DEFINED,
    "architect": State.ARCHITECTURE_LOCKED,
    "finalize": State.PHASE_PLAN_READY,
}
ALWAYS_ALLOWED = ("status", "reopen")
# Commands that add evidence in any of several open stages and never trigger a transition.
MULTI_STAGE: dict[str, tuple[State, ...]] = {
    "observe": (State.DISCOVERY, State.PRODUCT_MODEL),  # v2 observe mode
}

# The command suggested to work on (or enter) each stage.
PRIMARY_COMMAND: dict[State, str] = {
    State.DISCOVERY: "research",
    State.PRODUCT_MODEL: "features",
    State.SCOPE_DEFINED: "scope",
    State.ARCHITECTURE_LOCKED: "architect",
    State.PHASE_PLAN_READY: "finalize",
}

ALLOWED = "allowed"
NEEDS_TRANSITION = "needs_transition"
REFUSED = "refused"


@dataclass
class Decision:
    verdict: str
    command: str
    open_stage: str
    target_stage: str | None
    reason: str
    suggested_command: str | None
    gate: gates.GateReport | None = None
    missing_stages: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "command": self.command,
            "open_stage": self.open_stage,
            "target_stage": self.target_stage,
            "gate": self.gate.to_dict() if self.gate else None,
            "reason": self.reason,
            "suggested_command": self.suggested_command,
            "missing_stages": list(self.missing_stages),
        }


# The command that works on a failing gate condition, where a stage has several (v1.1 dogfood:
# status kept suggesting `features` after the feature conditions passed).
CONDITION_COMMAND: dict[str, str] = {
    "G-PM-SURFACE-FEATURES": "features",
    "G-PM-FEATURE-EVIDENCE": "features",
    "G-PM-WORKFLOW-PER-DOMAIN": "workflows",
    "G-PM-ENTITY-COMPLETE": "model",
    "G-PM-PERMISSIONS-COVERAGE": "model",
    "G-PM-INTEGRATIONS-COMPLETE": "model",
    "G-PM-INFERENCE-COMPLETE": "model",
}


COMPETITOR_CONDITION = "G-SC-COMPETITOR-SIGNAL"


def _competitors_missing(ws: Path) -> bool:
    """Fewer than ``competitors.min_researched`` active C records and no competitors waiver."""
    need = int(config.resolve("competitors.min_researched", ws))
    if competitors.researched(WorkspaceIndex(ws)) >= need:
        return False
    return waivers.get(ws, waivers.COMPETITORS) is None


def next_command(ws: Path, st: state.WorkspaceState, report: gates.GateReport | None = None) -> str:
    """Keep working on the open stage until its gate passes — on the command that addresses the
    first failing condition — then enter the next stage (`competitors` first when the scope
    stage would fail its competitor signal)."""
    report = report or gates.evaluate(ws, st.state.value)
    nxt = st.state.next()
    if st.state == State.SCOPE_DEFINED and COMPETITOR_CONDITION in report.failing():
        if _competitors_missing(ws):
            return "competitors"
    if report.passed and nxt in PRIMARY_COMMAND:
        if st.state == State.PRODUCT_MODEL and _competitors_missing(ws):
            return "competitors"
        return PRIMARY_COMMAND[nxt]
    for cid in report.failing():
        if cid in CONDITION_COMMAND:
            return CONDITION_COMMAND[cid]
    return PRIMARY_COMMAND.get(st.state, "status")


def check_command(ws: Path, cmd: str) -> Decision:
    st = state.load(ws)
    open_ = st.state
    if cmd in ALWAYS_ALLOWED:
        return Decision(ALLOWED, cmd, open_.value, None, f"{cmd} is always allowed", None)
    if cmd in MULTI_STAGE:
        stages_ = MULTI_STAGE[cmd]
        names = " and ".join(s.value for s in stages_)
        if open_ in stages_:
            why = f"{cmd} adds evidence in {names}; {open_.value} is open"
            return Decision(ALLOWED, cmd, open_.value, open_.value, why, cmd)
        last = stages_[-1]
        return Decision(REFUSED, cmd, open_.value, last.value,
                        f"{cmd} adds evidence only while {names} is open; re-open "
                        f'{last.value} with `/productforge reopen {last.value} --reason "…"` to '
                        "observe again (later stages become stale).",
                        f"reopen {last.value}")  # fmt: skip
    target = COMMAND_STAGE.get(cmd)
    if target is None:
        known = ", ".join([*COMMAND_STAGE, *MULTI_STAGE, *ALWAYS_ALLOWED])
        raise UsageError(
            f"unknown productforge command {cmd!r} (known: {known})", code="UNKNOWN_COMMAND"
        )
    if cmd == "competitors" and open_ == State.SCOPE_DEFINED:
        return Decision(
            ALLOWED,
            cmd,
            open_.value,
            open_.value,
            f"{cmd} adds evidence (C, FS, S records) as appends to the closed "
            f"{target.value}; {open_.value} is open",
            cmd,
        )
    if target == open_:
        return Decision(
            ALLOWED,
            cmd,
            open_.value,
            target.value,
            f"{cmd} belongs to the open stage {open_.value}",
            cmd,
        )
    if target.order < open_.order:
        return Decision(
            REFUSED,
            cmd,
            open_.value,
            target.value,
            f"{cmd} belongs to {target.value}, which is closed. To change it, re-open it with "
            f'`/productforge reopen {target.value} --reason "…"` (later stages become stale).',
            f"reopen {target.value}",
        )
    report = gates.evaluate(ws, open_.value)
    if target == open_.next():
        reason = f"{cmd} opens {target.value}; {open_.value} must pass its exit gate first" + (
            "" if report.passed else f" (failing: {', '.join(report.failing())})"
        )
        return Decision(
            NEEDS_TRANSITION,
            cmd,
            open_.value,
            target.value,
            reason,
            next_command(ws, st, report),
            report,
        )
    missing = tuple(s.value for s in state.ADVANCEABLE if open_.order < s.order < target.order)
    reason = (
        f"{cmd} belongs to {target.value}. Stages cannot be skipped: finish {open_.value}, "
        f"then {' and '.join(missing)} first."
    )
    return Decision(
        REFUSED,
        cmd,
        open_.value,
        target.value,
        reason,
        next_command(ws, st, report),
        report,
        missing,
    )
