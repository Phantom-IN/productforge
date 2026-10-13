from __future__ import annotations

import json
from pathlib import Path

from pflib import config, domain
from pflib.index import WorkspaceIndex


def test_gaps_list_unknown_cells_with_their_unknowns(tasklet_plan: Path) -> None:
    gaps = domain.permission_gaps(WorkspaceIndex(tasklet_plan))
    assert [(g["rule"], g["roles"], [u["id"] for u in g["unknowns"]]) for g in gaps] == [
        ("PR-002", ["RL-03 Member"], ["U-010"]),
        ("PR-003", ["RL-02 Admin"], ["U-010"]),
        ("PR-009", ["RL-03 Member"], ["U-009"]),
        ("PR-011", ["RL-03 Member"], ["U-011"]),
        ("PR-013", ["RL-03 Member"], ["U-011"]),
    ]
    assert gaps[2]["resource"] == "E-05" and gaps[2]["action"] == "delete"
    assert gaps[2]["unknowns"][0]["question"].startswith("Can members delete tasks")


def test_cli_ratio_and_limit(pf_cli, tasklet_plan: Path) -> None:  # type: ignore[no-untyped-def]
    code, out, _ = pf_cli("permission-gaps", "--workspace", str(tasklet_plan), "--json")
    payload = json.loads(out)
    assert code == 0 and (payload["cells"], payload["unknown"], payload["ratio"]) == (52, 5, 0.096)
    assert payload["over_limit"] is False and len(payload["gaps"]) == 5
    config.write_config(tasklet_plan, {"model.max_unknown_permission_ratio": 0.05})
    code, out, _ = pf_cli("permission-gaps", "--workspace", str(tasklet_plan), "--json")
    assert json.loads(out)["over_limit"] is True


def test_no_rules_no_gaps(tasklet_discovery: Path, pf_cli) -> None:  # type: ignore[no-untyped-def]
    code, out, _ = pf_cli("permission-gaps", "--workspace", str(tasklet_discovery), "--json")
    payload = json.loads(out)
    assert code == 0 and payload["cells"] == 0 and payload["ratio"] == 0.0 and payload["gaps"] == []
