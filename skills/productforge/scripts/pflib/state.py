"""Lifecycle state machine (IMPLEMENTATION_PLAN.md §7).

The state names the **open stage** — the only stage whose artifacts may change. Moves are
strictly one stage forward (after the closing stage's gate passes and the user confirms),
or back to an earlier stage via ``reopen`` (feedback loop), which marks every later stage
that had already been worked on as *stale*. Entering a stage clears its stale flag.

``.productforge/state.json`` is written only by this module (through ``pf.py``).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from pflib import catalog, records, stages
from pflib.errors import CheckFailed, UsageError
from pflib.index import WorkspaceIndex
from pflib.io import atomic_write_text

SCHEMA_VERSION = 1
STATE_FILE = "state.json"
SCOPE_SOURCES = ("user", "recommended")


class State(StrEnum):
    UNINITIALIZED = stages.UNINITIALIZED
    DISCOVERY = stages.DISCOVERY
    PRODUCT_MODEL = stages.PRODUCT_MODEL
    SCOPE_DEFINED = stages.SCOPE_DEFINED
    ARCHITECTURE_LOCKED = stages.ARCHITECTURE_LOCKED
    PHASE_PLAN_READY = stages.PHASE_PLAN_READY
    IMPLEMENTATION = stages.IMPLEMENTATION

    @property
    def order(self) -> int:
        return stages.ORDER.index(self.value)

    def next(self) -> State | None:
        i = self.order + 1
        return State(stages.ORDER[i]) if i < len(stages.ORDER) else None


# Stages ``advance`` can move between (IMPLEMENTATION is reported, never advanced into).
ADVANCEABLE: tuple[State, ...] = tuple(State(s) for s in stages.ARTIFACT_STAGES)


def parse_state(value: str) -> State:
    try:
        return State(value.upper())
    except ValueError:
        known = ", ".join(s.value for s in State)
        raise UsageError(
            f"unknown stage {value!r} (known: {known})", code="UNKNOWN_STAGE"
        ) from None


@dataclass
class WorkspaceState:
    product: dict[str, Any]
    scope: dict[str, Any] = field(
        default_factory=lambda: {"text": None, "source": None, "accepted": False}
    )
    state: State = State.DISCOVERY
    stale: list[str] = field(default_factory=list)
    stages: dict[str, dict[str, str | None]] = field(default_factory=dict)
    locks: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "product": self.product,
            "scope": self.scope,
            "state": self.state.value,
            "stale": self.stale,
            "stages": self.stages,
            "locks": self.locks,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkspaceState:
        problems = validate_dict(data)
        if problems:
            raise CheckFailed(
                "invalid state.json: " + "; ".join(problems),
                code="BAD_STATE",
                details={"problems": problems},
            )
        return cls(
            product=data["product"],
            scope=data["scope"],
            state=State(data["state"]),
            stale=list(data["stale"]),
            stages=data["stages"],
            locks=data["locks"],
            schema_version=data["schema_version"],
        )


def validate_dict(data: Any) -> list[str]:
    """Human-readable problems with a state.json payload (empty list = valid)."""
    if not isinstance(data, dict):
        return ["top level must be an object"]
    problems: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"schema_version must be {SCHEMA_VERSION}")
    expected = {
        "product": dict,
        "scope": dict,
        "state": str,
        "stale": list,
        "stages": dict,
        "locks": dict,
    }
    for key, typ in expected.items():
        if not isinstance(data.get(key), typ):
            problems.append(f"{key} must be a {typ.__name__}")
    if problems:
        return problems
    names = {s.value for s in State}
    if data["state"] not in names:
        problems.append(f"unknown state {data['state']!r}")
    for key in ("name", "target_url", "slug", "our_name"):
        if not isinstance(data["product"].get(key), str) or not data["product"][key]:
            problems.append(f"product.{key} must be a non-empty string")
    scope = data["scope"]
    if scope.get("text") is not None and not isinstance(scope.get("text"), str):
        problems.append("scope.text must be a string or null")
    if scope.get("source") not in (None, *SCOPE_SOURCES):
        problems.append("scope.source must be user, recommended or null")
    if not isinstance(scope.get("accepted"), bool):
        problems.append("scope.accepted must be a boolean")
    for name in data["stale"]:
        if name not in names:
            problems.append(f"unknown stale stage {name!r}")
    for name in list(data["stages"]) + list(data["locks"]):
        if name not in names:
            problems.append(f"unknown stage key {name!r}")
    return problems


def state_path(ws: Path) -> Path:
    from pflib.workspace import pf_dir

    return pf_dir(ws) / STATE_FILE


def load(ws: Path) -> WorkspaceState:
    path = state_path(ws)
    if not path.exists():
        raise CheckFailed(f"{path} is missing", code="BAD_STATE")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CheckFailed(f"{path} is not valid JSON: {exc}", code="BAD_STATE") from exc
    return WorkspaceState.from_dict(data)


def save(ws: Path, st: WorkspaceState) -> None:
    atomic_write_text(state_path(ws), json.dumps(st.to_dict(), indent=2) + "\n")


def _stage_entry(st: WorkspaceState, stage: State) -> dict[str, str | None]:
    return st.stages.setdefault(stage.value, {"opened_at": None, "completed_at": None})


def open_stage(st: WorkspaceState, stage: State, now: str) -> None:
    entry = _stage_entry(st, stage)
    entry["opened_at"] = now
    entry["completed_at"] = None
    st.state = stage
    if stage.value in st.stale:
        st.stale.remove(stage.value)


def check_transition(st: WorkspaceState, to: State) -> None:
    """Raise ``ILLEGAL_TRANSITION`` unless ``to`` is exactly the stage after the open one."""
    current = st.state
    nxt = current.next()
    if to not in ADVANCEABLE or nxt != to:
        expected = nxt.value if nxt in ADVANCEABLE else "none (final stage)"
        raise UsageError(
            f"cannot advance from {current.value} to {to.value}: only the next stage "
            f"({expected}) can be opened, one stage at a time",
            code="ILLEGAL_TRANSITION",
        )


def transition(st: WorkspaceState, to: State, now: str) -> None:
    """Move from the open stage to exactly the next one (gate checking is the caller's job)."""
    check_transition(st, to)
    current = st.state
    _stage_entry(st, current)["completed_at"] = now
    open_stage(st, to, now)


def reopen(st: WorkspaceState, stage: State, reason: str) -> list[str]:
    """Re-open an earlier stage. Returns the stages marked stale."""
    if not reason.strip():
        raise UsageError("reopen needs a non-empty --reason", code="REOPEN_NEEDS_REASON")
    if stage not in ADVANCEABLE or stage.order >= st.state.order:
        raise UsageError(
            f"can only reopen a stage before the open stage {st.state.value}",
            code="ILLEGAL_REOPEN",
        )
    worked = {
        s.value
        for s in ADVANCEABLE
        if s.order > stage.order and st.stages.get(s.value, {}).get("opened_at")
    }
    stale = sorted(set(st.stale) | worked, key=stages.ORDER.index)
    for s in ADVANCEABLE:
        if s.order >= stage.order:
            st.locks.pop(s.value, None)
            if s.value in st.stages:
                st.stages[s.value]["completed_at"] = None
    st.stale = stale
    st.state = stage
    return stale


# ----------------------------------------------------------------------------- locks


def record_lock(rec: records.Record, schema: catalog.RecordSchema) -> dict[str, Any]:
    """Lock snapshot of one record: hash of everything except union-field references,
    plus the set of union references (so evidence may later be appended, never removed)."""
    fixed = {
        "title": rec.title,
        "fields": [[k, rec.fields[k]] for k in rec.order if k not in schema.union_fields],
    }
    digest = hashlib.sha256(json.dumps(fixed, ensure_ascii=False).encode("utf-8")).hexdigest()
    refs = sorted({r for k in schema.union_fields for r in records.parse_refs(rec.get(k))})
    return {"hash": digest, "refs": refs}


def snapshot_locks(ws: Path, stage: State) -> dict[str, dict[str, Any]]:
    """Lock snapshots for every canonical record owned by ``stage``."""
    index = WorkspaceIndex(ws)
    out: dict[str, dict[str, Any]] = {}
    for _spec, schema in catalog.schemas_for_stage(stage.value):
        for _rel, rec in index.records(schema.prefix):
            out[rec.id] = record_lock(rec, schema)
    return dict(sorted(out.items()))
