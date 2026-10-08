from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

Cli = Callable[..., tuple[int, str, str]]

SOURCE = (
    "### S-?1 — Docs\n- URL: https://docs.tasklet.example/a\n"
    "- Canonical URL: https://docs.tasklet.example/a\n- Category: docs\n- Tier: 1\n"
    "- Authority: High\n- Relevant area: Tasks\n- Published: unknown\n"
    "- Last inspected: 2026-10-08\n- Notes:\n"
)


def test_no_workspace_is_a_usage_error(pf_cli: Cli, tmp_path: Path) -> None:
    code, out, _ = pf_cli("next-id", "D", "--json", cwd=tmp_path)
    assert code == 2
    assert json.loads(out)["error"] == "NO_WORKSPACE"


def test_staging_merge_next_id_round_trip(pf_cli: Cli, tmp_path: Path) -> None:
    (tmp_path / ".productforge").mkdir()
    code, out, err = pf_cli("staging", "new", "--role", "research-agent", "--json", cwd=tmp_path)
    assert code == 0, err
    run = json.loads(out)
    staged = Path(run["path"]) / "research" / "sources.md"
    staged.parent.mkdir(parents=True)
    staged.write_text(SOURCE, encoding="utf-8")

    code, out, err = pf_cli("merge", run["run_id"], "--workspace", str(tmp_path), "--json")
    assert code == 0, err
    report = json.loads(out)
    assert report["added"] == {"S": 1} and report["id_map"] == {"S-?1": "S-001"}

    code, out, _ = pf_cli("next-id", "S", "--json", cwd=tmp_path / "research")  # discovery upward
    assert code == 0 and json.loads(out) == {"id": "S-002"}
    code, out, _ = pf_cli("next-id", "S", cwd=tmp_path)
    assert out.strip() == "id: S-003"


def test_merge_failure_exits_1_with_details(pf_cli: Cli, tmp_path: Path) -> None:
    (tmp_path / ".productforge").mkdir()
    _, out, _ = pf_cli("staging", "new", "--role", "research-agent", "--json", cwd=tmp_path)
    run = json.loads(out)
    ledger = Path(run["path"]) / "research" / "DISCOVERY_LEDGER.md"
    ledger.parent.mkdir(parents=True)
    ledger.write_text("### D-?1 — x\n- Claim: x\n- Evidence: S-?4\n", encoding="utf-8")
    code, out, err = pf_cli("merge", run["run_id"], "--json", cwd=tmp_path)
    assert code == 1
    payload = json.loads(out)
    assert payload["error"] == "DANGLING_PROVISIONAL"
    assert payload["details"] == {"ids": ["S-?4"]}
    assert "S-?4" in err


def test_bad_prefix_and_role(pf_cli: Cli, tmp_path: Path) -> None:
    (tmp_path / ".productforge").mkdir()
    code, out, _ = pf_cli("next-id", "ZZ", "--json", cwd=tmp_path)
    assert code == 2 and json.loads(out)["error"] == "UNKNOWN_PREFIX"
    code, out, _ = pf_cli("staging", "new", "--role", "Bad Role", "--json", cwd=tmp_path)
    assert code == 2 and json.loads(out)["error"] == "BAD_ROLE"
