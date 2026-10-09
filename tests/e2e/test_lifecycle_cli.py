from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Callable
from pathlib import Path

import pytest

import pf
from pflib import state, workspace
from pflib.state import State

Cli = Callable[..., tuple[int, str, str]]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, dict]:
    code = pf.main([*argv, "--json"])
    out = capsys.readouterr().out
    return code, json.loads(out)


# ----------------------------------------------------------- subprocess (real gates)


def test_init_status_check_advance_flow(pf_cli: Cli, tmp_path: Path) -> None:
    ws = tmp_path / "tl"
    code, out, err = pf_cli(
        "init", "https://tasklet.example", "--out", str(ws), "--scope", "task tracking", "--json"
    )
    assert code == 0, err
    init = json.loads(out)
    assert init["state"] == "DISCOVERY" and init["needs_rename"] is True
    assert init["our_name"] == "tasklet-alt" and init["next_command"] == "research"

    code, out, _ = pf_cli("status", "--workspace", str(ws), "--json")
    status = json.loads(out)
    assert code == 0
    assert status["open_stage"] == "DISCOVERY"
    assert not any(status["counts"].values()) and not any(status["summary"].values())
    assert status["next_command"] == "research"

    code, out, _ = pf_cli("status", cwd=ws / "research")
    assert "Product discovered: Tasklet" in out and "Next command: /productforge research" in out

    code, out, _ = pf_cli("check-command", "architect", "--workspace", str(ws), "--json")
    decision = json.loads(out)
    assert code == 0 and decision["verdict"] == "refused"
    assert decision["missing_stages"] == ["PRODUCT_MODEL", "SCOPE_DEFINED"]

    before = sha(ws / ".productforge/state.json")
    code, out, _ = pf_cli(
        "advance", "--to", "PRODUCT_MODEL", "--confirmed", "--workspace", str(ws), "--json"
    )
    result = json.loads(out)
    assert code == 1 and result["passed"] is False and result["transitioned"] is False
    statuses = {r["id"]: r["status"] for r in result["gate"]["results"]}
    assert statuses["G-SCOPE-SET"] == "pass" and statuses["G-DISC-TIER1"] == "fail"
    assert sha(ws / ".productforge/state.json") == before

    code, out, _ = pf_cli("advance", "--to", "SCOPE_DEFINED", "--workspace", str(ws), "--json")
    assert code == 2 and json.loads(out)["error"] == "ILLEGAL_TRANSITION"


def test_status_outside_workspace_keeps_phase_00_behaviour(pf_cli: Cli, tmp_path: Path) -> None:
    code, out, _ = pf_cli("status", "--json", cwd=tmp_path)
    assert code == 0 and json.loads(out) == {
        "workspace": None,
        "message": "No ProductForge workspace found",
    }
    code, out, _ = pf_cli("status", "--workspace", str(tmp_path), "--json")
    assert code == 2 and json.loads(out)["error"] == "NO_WORKSPACE"


def test_set_scope_cli(pf_cli: Cli, tmp_path: Path) -> None:
    ws = tmp_path / "w"
    pf_cli("init", "https://tasklet.example", "--out", str(ws))
    code, out, _ = pf_cli(
        "set-scope",
        "task lists",
        "--accepted",
        "--source",
        "recommended",
        "--workspace",
        str(ws),
        "--json",
    )
    assert code == 0
    assert json.loads(out)["scope"] == {
        "text": "task lists",
        "source": "recommended",
        "accepted": True,
    }


# ------------------------------------------------- in-process (controllable gates)


def test_confirmed_advance_snapshots_locks_and_logs(
    new_ws: Path, gate_control: object, capsys: pytest.CaptureFixture[str]
) -> None:
    (new_ws / "research/sources.md").write_text(
        "### S-001 — Docs\n- URL: https://docs.tasklet.example/a\n"
        "- Canonical URL: https://docs.tasklet.example/a\n- Category: docs\n- Tier: 1\n"
        "- Authority: High\n- Relevant area: Tasks\n- Published: unknown\n"
        "- Last inspected: 2026-10-08\n- Notes:\n"
    )
    (new_ws / "research/DISCOVERY_LEDGER.md").write_text(
        "### D-001 — a\n- Claim: a\n- Evidence: S-001\n- Confidence: CONFIRMED\n"
        "- Product impact:\n- Engineering impact:\n- Status: active\n"
    )
    ws = str(new_ws)
    before = sha(new_ws / ".productforge/state.json")
    code, payload = run(capsys, "advance", "--to", "PRODUCT_MODEL", "--workspace", ws)
    assert code == 0 and payload["passed"] and not payload["transitioned"]
    assert sha(new_ws / ".productforge/state.json") == before  # unconfirmed → untouched

    code, payload = run(
        capsys, "advance", "--to", "PRODUCT_MODEL", "--confirmed", "--workspace", ws
    )
    assert code == 0 and payload["transitioned"] and payload["open_stage"] == "PRODUCT_MODEL"
    st = state.load(new_ws)
    assert st.state == State.PRODUCT_MODEL
    assert set(st.locks["DISCOVERY"]) == {"D-001", "S-001"}
    assert st.locks["DISCOVERY"]["D-001"]["refs"] == ["S-001"]
    assert workspace.read_history(new_ws)[-1]["event"] == "advance"

    code, payload = run(
        capsys, "reopen", "DISCOVERY", "--reason", "more sources", "--workspace", ws
    )
    assert code == 0 and payload == {
        "open_stage": "DISCOVERY",
        "stale": ["PRODUCT_MODEL"],
        "reason": "more sources",
    }
    assert state.load(new_ws).locks == {}
    code, payload = run(capsys, "status", "--workspace", ws)
    assert payload["stale"] == ["PRODUCT_MODEL"] and payload["gate_progress"]["passed"]
    assert payload["next_command"] == "features"


@pytest.mark.parametrize("seed", range(8))
def test_random_sequences_never_skip_or_pass_failing_gates(
    new_ws: Path, gate_control: object, capsys: pytest.CaptureFixture[str], seed: int
) -> None:
    rng = random.Random(seed)
    ws = str(new_ws)
    stage_names = [s.value for s in State]
    advances = 0
    for _ in range(60):
        before_state = state.load(new_ws).state
        before_hash = sha(new_ws / ".productforge/state.json")
        gate_control.reset()  # type: ignore[attr-defined]
        gate_fails = rng.random() < 0.4
        if gate_fails:
            # one stage-specific (stubbed) condition per stage
            gate_control.fail(  # type: ignore[attr-defined]
                "G-DISC-TIER1",
                "G-PM-FEATURE-EVIDENCE",
                "G-SC-ALL-SCORED",
                "G-AR-STACK-COMPLETE",
                "G-PP-PHASE-LINT",
            )
        op = rng.choice(["advance", "advance", "advance", "reopen", "status", "check"])
        nxt = before_state.next()
        if nxt is not None and rng.random() < 0.5:
            target = nxt.value
        else:
            target = rng.choice(stage_names)
        confirmed = rng.random() < 0.7
        if op == "advance":
            argv = ["advance", "--to", target, "--workspace", ws] + (
                ["--confirmed"] if confirmed else []
            )
        elif op == "reopen":
            argv = ["reopen", target, "--reason", "fuzz", "--workspace", ws]
        elif op == "check":
            argv = [
                "check-command",
                rng.choice(["research", "features", "scope", "architect", "finalize"]),
                "--workspace",
                ws,
            ]
        else:
            argv = ["status", "--workspace", ws]
        pf.main([*argv, "--json"])
        capsys.readouterr()
        after_state = state.load(new_ws).state
        if after_state.order > before_state.order:
            assert op == "advance" and confirmed and not gate_fails
            assert after_state.order == before_state.order + 1
            assert target == after_state.value
            advances += 1
        if op in ("status", "check") or (op == "advance" and (not confirmed or gate_fails)):
            assert sha(new_ws / ".productforge/state.json") == before_hash
        if after_state.order < before_state.order:
            assert op == "reopen"
    assert advances >= 2, f"seed {seed} exercised too few transitions"
