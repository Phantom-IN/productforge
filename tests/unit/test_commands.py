from __future__ import annotations

from pathlib import Path

import pytest

from pflib import commands, state
from pflib.errors import PFError
from pflib.state import State


def _move(ws: Path, to: State) -> None:
    st = state.load(ws)
    state.transition(st, to, "2026-10-08T00:00:00Z")
    state.save(ws, st)


def test_allowed_for_open_stage(new_ws: Path) -> None:
    d = commands.check_command(new_ws, "research")
    assert d.verdict == commands.ALLOWED and d.target_stage == "DISCOVERY"
    assert commands.check_command(new_ws, "status").verdict == commands.ALLOWED


def test_next_stage_needs_transition_with_gate(new_ws: Path) -> None:
    d = commands.check_command(new_ws, "features")
    assert d.verdict == commands.NEEDS_TRANSITION
    assert d.target_stage == "PRODUCT_MODEL"
    assert d.gate is not None and not d.gate.passed
    assert d.suggested_command == "research"  # gate not passing → keep researching


def test_needs_transition_suggests_next_when_gate_passes(
    new_ws: Path, gate_control: object
) -> None:
    d = commands.check_command(new_ws, "workflows")
    assert d.verdict == commands.NEEDS_TRANSITION and d.gate is not None and d.gate.passed
    assert d.suggested_command == "features"


def test_skipping_ahead_is_refused_naming_missing_stages(new_ws: Path) -> None:
    d = commands.check_command(new_ws, "architect")
    assert d.verdict == commands.REFUSED
    assert d.missing_stages == ("PRODUCT_MODEL", "SCOPE_DEFINED")
    assert "PRODUCT_MODEL and SCOPE_DEFINED" in d.reason
    assert d.suggested_command == "research"


def test_closed_stage_is_refused_with_reopen(new_ws: Path) -> None:
    _move(new_ws, State.PRODUCT_MODEL)
    d = commands.check_command(new_ws, "research")
    assert d.verdict == commands.REFUSED
    assert d.suggested_command == "reopen DISCOVERY"
    assert "reopen DISCOVERY" in d.reason


def test_after_reopen_later_commands_are_refused_until_regated(new_ws: Path) -> None:
    for s in (State.PRODUCT_MODEL, State.SCOPE_DEFINED):
        _move(new_ws, s)
    st = state.load(new_ws)
    state.reopen(st, State.DISCOVERY, "need more sources")
    state.save(new_ws, st)
    assert commands.check_command(new_ws, "scope").verdict == commands.REFUSED
    assert commands.check_command(new_ws, "features").verdict == commands.NEEDS_TRANSITION
    assert commands.check_command(new_ws, "research").verdict == commands.ALLOWED


def test_unknown_command(new_ws: Path) -> None:
    with pytest.raises(PFError) as info:
        commands.check_command(new_ws, "deploy")
    assert info.value.code == "UNKNOWN_COMMAND"


def test_every_stage_has_a_primary_command() -> None:
    for stage in state.ADVANCEABLE:
        assert commands.COMMAND_STAGE[commands.PRIMARY_COMMAND[stage]] == stage
