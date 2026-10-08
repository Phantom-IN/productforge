from __future__ import annotations

import json
from pathlib import Path

import pytest

from pflib import catalog, records, state
from pflib.errors import PFError
from pflib.state import State

NOW = "2026-10-08T00:00:00Z"


def fresh() -> state.WorkspaceState:
    st = state.WorkspaceState(
        product={
            "name": "Tasklet",
            "target_url": "https://tasklet.example",
            "slug": "tasklet",
            "our_name": "tasklet-alt",
            "needs_rename": True,
        },
    )
    state.open_stage(st, State.DISCOVERY, NOW)
    return st


def test_only_the_next_stage_can_be_opened() -> None:
    st = fresh()
    for bad in (State.SCOPE_DEFINED, State.DISCOVERY, State.UNINITIALIZED, State.IMPLEMENTATION):
        with pytest.raises(PFError) as info:
            state.transition(st, bad, NOW)
        assert info.value.code == "ILLEGAL_TRANSITION"
    state.transition(st, State.PRODUCT_MODEL, NOW)
    assert st.state == State.PRODUCT_MODEL
    assert st.stages["DISCOVERY"]["completed_at"] == NOW
    assert st.stages["PRODUCT_MODEL"] == {"opened_at": NOW, "completed_at": None}


def test_final_stage_cannot_advance() -> None:
    st = fresh()
    for s in (
        State.PRODUCT_MODEL,
        State.SCOPE_DEFINED,
        State.ARCHITECTURE_LOCKED,
        State.PHASE_PLAN_READY,
    ):
        state.transition(st, s, NOW)
    with pytest.raises(PFError) as info:
        state.transition(st, State.IMPLEMENTATION, NOW)
    assert "none (final stage)" in info.value.message


def test_reopen_marks_worked_later_stages_stale_and_drops_locks() -> None:
    st = fresh()
    for s in (State.PRODUCT_MODEL, State.SCOPE_DEFINED, State.ARCHITECTURE_LOCKED):
        st.locks[st.state.value] = {"X-1": {}}
        state.transition(st, s, NOW)
    stale = state.reopen(st, State.PRODUCT_MODEL, "missing integrations")
    assert st.state == State.PRODUCT_MODEL
    assert stale == ["SCOPE_DEFINED", "ARCHITECTURE_LOCKED"]
    assert set(st.locks) == {"DISCOVERY"}
    assert st.stages["PRODUCT_MODEL"]["completed_at"] is None
    # re-entering a stale stage clears its flag; the other stays stale
    state.transition(st, State.SCOPE_DEFINED, NOW)
    assert st.stale == ["ARCHITECTURE_LOCKED"]


def test_reopen_rules() -> None:
    st = fresh()
    state.transition(st, State.PRODUCT_MODEL, NOW)
    with pytest.raises(PFError) as info:
        state.reopen(st, State.DISCOVERY, "  ")
    assert info.value.code == "REOPEN_NEEDS_REASON"
    for bad in (State.PRODUCT_MODEL, State.SCOPE_DEFINED, State.UNINITIALIZED):
        with pytest.raises(PFError) as info:
            state.reopen(st, bad, "why")
        assert info.value.code == "ILLEGAL_REOPEN"


def test_save_load_round_trip_and_validation(tmp_path: Path) -> None:
    (tmp_path / ".productforge").mkdir()
    st = fresh()
    state.save(tmp_path, st)
    assert state.load(tmp_path).to_dict() == st.to_dict()
    data = json.loads(state.state_path(tmp_path).read_text())
    data["state"] = "LAUNCHED"
    data["scope"]["source"] = "guess"
    state.state_path(tmp_path).write_text(json.dumps(data))
    with pytest.raises(PFError) as info:
        state.load(tmp_path)
    assert info.value.code == "BAD_STATE"
    assert "unknown state 'LAUNCHED'" in info.value.details["problems"]


def test_parse_state() -> None:
    assert state.parse_state("product_model") is State.PRODUCT_MODEL
    with pytest.raises(PFError):
        state.parse_state("nope")


def test_lock_snapshot_is_stable_and_ignores_union_ref_growth() -> None:
    _, schema = catalog.schema_for_prefix("D")
    text = (
        "### D-001 — Claim\n- Claim: x\n- Evidence: S-001\n- Confidence: CONFIRMED\n"
        "- Product impact:\n- Engineering impact:\n- Status: active\n"
    )
    rec = records.parse_document(text).records[0]
    a = state.record_lock(rec, schema)
    assert a == state.record_lock(records.parse_document(text).records[0], schema)
    grown = records.parse_document(text.replace("S-001", "S-001, S-002")).records[0]
    b = state.record_lock(grown, schema)
    assert b["hash"] == a["hash"] and b["refs"] == ["S-001", "S-002"]
    edited = records.parse_document(text.replace("CONFIRMED", "PROBABLE")).records[0]
    assert state.record_lock(edited, schema)["hash"] != a["hash"]
