from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

Cli = Callable[..., tuple[int, str, str]]


def test_brief_and_merge_check_cli(pf_cli: Cli, tasklet_discovery: Path) -> None:
    ws = str(tasklet_discovery)
    code, out, err = pf_cli(
        "brief",
        "--role",
        "research-agent",
        "--task",
        "Collect sources.",
        "--input",
        "research/sources.md",
        "--workspace",
        ws,
        "--json",
    )
    assert code == 0, err
    payload = json.loads(out)
    assert set(payload) == {
        "run_id",
        "staging_path",
        "repair",
        "findings",
        "max_repair_loops",
        "brief",
    }
    code, out, _ = pf_cli("brief", "--role", "research-agent", "--task", "x", "--workspace", ws)
    assert out.startswith("# ProductForge brief — research-agent")

    staged = Path(payload["staging_path"]) / "research" / "DISCOVERY_LEDGER.md"
    staged.parent.mkdir(parents=True)
    staged.write_text(
        "### D-?1 — Exports exist\n- Claim: x\n- Evidence: S-010\n- Confidence: CONFIRMED\n"
        "- Product impact:\n- Engineering impact:\n- Status: active\n"
    )
    code, out, _ = pf_cli("merge", payload["run_id"], "--check", "--workspace", ws, "--json")
    assert code == 1 and json.loads(out)["findings"][0]["code"] == "CONFIDENCE_RULE"
    code, out, _ = pf_cli(
        "brief",
        "--role",
        "research-agent",
        "--task",
        "Fix.",
        "--run-id",
        payload["run_id"],
        "--workspace",
        ws,
        "--json",
    )
    assert code == 0 and json.loads(out)["repair"] is True
