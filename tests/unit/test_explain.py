from __future__ import annotations

from pathlib import Path

import pytest

from pflib import trace
from pflib.errors import UsageError


def ids(nodes: list[dict]) -> list[str]:  # type: ignore[type-arg]
    out = []
    for n in nodes:
        out.append(n["id"])
        out += ids(n["children"])
    return out


def test_explain_walks_both_ways(tasklet_plan: Path) -> None:
    out = trace.explain(tasklet_plan, "R-010")
    assert ["A-010", "D-039", "S-001"] == [i for i in ids(out["upstream"]) if i[0] in "ADS"]
    assert {"ADR-008", "Phase 10"} <= set(ids(out["downstream"]))


def test_explain_a_phase(tasklet_plan: Path) -> None:
    out = trace.explain(tasklet_plan, "Phase 07")
    assert {"R-002", "ADR-006"} <= set(ids(out["upstream"]))


def test_explain_cli_text(pf_cli, tasklet_plan: Path) -> None:  # type: ignore[no-untyped-def]
    code, out, _ = pf_cli("explain", "R-010", "--workspace", str(tasklet_plan))
    assert code == 0
    assert "← S-001 (Tier 1) https://docs.tasklet.example/tasks  [Evidence]" in out
    assert "→ ADR-008 Object storage with signed URLs  [Satisfies]" in out


def test_unknown_id(tasklet_plan: Path) -> None:
    with pytest.raises(UsageError):
        trace.explain(tasklet_plan, "R-999")
