from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from conftest import copy_snapshot

Cli = Callable[..., tuple[int, str, str]]


def snapshot(ws: Path) -> dict[str, bytes]:
    return {str(p.relative_to(ws)): p.read_bytes() for p in sorted(ws.rglob("*")) if p.is_file()}


def test_dry_run_prints_the_next_session_and_changes_nothing(pf_cli: Cli, tmp_path: Path) -> None:
    ws = copy_snapshot("DISCOVERY_FAILING", tmp_path / "ws")
    before = snapshot(ws)
    code, out, _ = pf_cli("auto", "start", "--dry-run", "--workspace", str(ws), "--json")
    data = json.loads(out)
    assert code == 0 and data["dry_run"] is True and data["stopped"] is None
    argv = data["next_session"]
    assert argv[:3] == ["claude", "-p", "/productforge research"] and "--plugin-dir" in argv
    assert snapshot(ws) == before
    code, text, _ = pf_cli("auto", "start", "--dry-run", "--workspace", str(ws))
    assert code == 0 and "claude -p '/productforge research'" in text and snapshot(ws) == before


def test_dry_run_on_a_passing_gate_names_the_transition(pf_cli: Cli, tmp_path: Path) -> None:
    ws = copy_snapshot("DISCOVERY", tmp_path / "ws")
    before = snapshot(ws)
    code, out, _ = pf_cli("auto", "start", "--dry-run", "--workspace", str(ws), "--json")
    assert code == 0 and json.loads(out)["next"] == "advance --to PRODUCT_MODEL --auto"
    assert snapshot(ws) == before
