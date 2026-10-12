from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from pflib import brief, config, gates, merge, workspace
from pflib.errors import PFError


def test_pending_runs_lists_unmerged_runs_with_counts(tasklet_discovery: Path) -> None:
    empty, _ = workspace.create_staging_run(tasklet_discovery, "research-agent")
    full, path = workspace.create_staging_run(tasklet_discovery, "product-analyst")
    (path / "research").mkdir()
    (path / "research/product-surfaces.md").write_text(
        "### PS-?1 — A\n- Purpose: x\n\n### PS-?2 — B\n"
    )
    (path / "raw").mkdir()
    (path / "raw/report.md").write_text("### S-?9 — not counted\n")
    pending = {p["run_id"]: p for p in workspace.pending_runs(tasklet_discovery)}
    assert pending[empty]["files"] == 0 and pending[empty]["blocks"] == 0
    assert pending[full]["role"] == "product-analyst"
    assert (
        pending[full]["files"] == 1
        and pending[full]["blocks"] == 2
        and pending[full]["raw_files"] == 1
    )


def test_discard_archives_the_run_and_unblocks_the_gate(tasklet_discovery: Path) -> None:
    run_id, _ = workspace.create_staging_run(tasklet_discovery, "research-agent")
    assert "G-NO-UNMERGED-STAGING" in gates.evaluate(tasklet_discovery, "DISCOVERY").failing()
    with pytest.raises(PFError) as info:
        workspace.discard_run(tasklet_discovery, run_id, " ")
    assert info.value.code == "DISCARD_NEEDS_REASON"
    dest = workspace.discard_run(tasklet_discovery, run_id, "agent was cut off before writing")
    assert dest.is_dir() and dest.parent.name == workspace.DISCARDED
    assert workspace.pending_runs(tasklet_discovery) == []
    assert gates.evaluate(tasklet_discovery, "DISCOVERY").passed
    assert workspace.read_history(tasklet_discovery)[-1]["event"] == "discard"
    with pytest.raises(PFError) as info:
        merge.merge(tasklet_discovery, run_id)
    assert info.value.code == "NO_SUCH_RUN"


def test_brief_refuses_new_runs_beyond_the_pending_limit(tasklet_discovery: Path) -> None:
    config.write_config(tasklet_discovery, {"agents.max_pending_runs": 2})
    first = brief.render(tasklet_discovery, role="research-agent", task="a")
    brief.render(tasklet_discovery, role="research-agent", task="b")
    with pytest.raises(PFError) as info:
        brief.render(tasklet_discovery, role="research-agent", task="c")
    assert info.value.code == "RUN_LIMIT" and first.run_id in info.value.details["pending"]
    with pytest.raises(PFError):
        brief.render_delegation(tasklet_discovery, "anthropic-skills:pdf", "x")
    # a repair brief for an existing run is always allowed
    again = brief.render(tasklet_discovery, role="research-agent", task="a", run_id=first.run_id)
    assert again.run_id == first.run_id
    merge.merge(tasklet_discovery, first.run_id)  # merging frees a slot
    assert brief.render(tasklet_discovery, role="research-agent", task="c").run_id


def test_staging_cli(pf_cli: Callable[..., tuple[int, str, str]], tasklet_discovery: Path) -> None:
    ws = str(tasklet_discovery)
    code, out, _ = pf_cli("staging", "new", "--role", "research-agent", "--workspace", ws, "--json")
    run_id = json.loads(out)["run_id"]
    code, out, _ = pf_cli("staging", "list", "--workspace", ws, "--json")
    assert [p["run_id"] for p in json.loads(out)["pending"]] == [run_id]
    code, out, _ = pf_cli("staging", "discard", run_id, "--workspace", ws, "--json")
    assert code == 2 and json.loads(out)["error"] == "USAGE_ERROR"
    code, out, _ = pf_cli("staging", "discard", run_id, "--reason", "empty", "--workspace", ws,
                          "--json")  # fmt: skip
    assert code == 0 and json.loads(out)["discarded"] == run_id
    code, out, _ = pf_cli("staging", "new", "--workspace", ws, "--json")
    assert code == 2
