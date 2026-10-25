from __future__ import annotations

import json
from pathlib import Path

from pflib import render, score, trace


def test_every_v1_requirement_traces_from_a_source_to_a_phase(tasklet_plan: Path) -> None:
    rep = trace.report(tasklet_plan)
    assert rep["requirements"] == rep["fully_traced"] == 11 and rep["findings"] == []
    built = {r.feature for r in score.evaluate(tasklet_plan) if r.decision in score.IN_V1}
    for rid, c in rep["chains"].items():
        assert c["sources"] and c["claims"] and c["phases"], rid
    assert built  # the chains above cover every V1 feature's requirement (gate-checked)


def test_chain_contents(tasklet_plan: Path) -> None:
    c = trace.chain(trace.build(tasklet_plan), "R-010")
    assert c["sources"] == ["S-001"] and c["claims"] == ["D-039"]
    assert (
        c["inferences"] == ["A-010"]
        and c["adrs"] == ["ADR-008", "ADR-015"]
        and c["phases"] == ["Phase 10"]
    )


def test_structural_links_are_not_provenance(tasklet_plan: Path) -> None:
    # E-08 Attachment → E-05 Task (Relationships) must not drag the task's claims into R-010
    c = trace.chain(trace.build(tasklet_plan), "R-010")
    assert "D-001" not in c["claims"] and c["entities"] == ["E-08"]


def test_traceability_view(tasklet_plan: Path) -> None:
    text = (tasklet_plan / "spec/TRACEABILITY.md").read_text()
    regions = render.regions(text)
    assert "| R-010 | S-001 | D-039 | F-006 | A-010 | ADR-008, ADR-015 | 10 |" in regions["chains"]
    assert "| Traced from a source to a phase | 11 |" in regions["coverage"]
    assert regions["gaps"] == "_None._\n"


def test_trace_cli(pf_cli, tasklet_plan: Path) -> None:  # type: ignore[no-untyped-def]
    (tasklet_plan / "spec/TRACEABILITY.md").unlink()
    code, out, _ = pf_cli("trace", "--write", "--workspace", str(tasklet_plan), "--json")
    payload = json.loads(out)
    assert code == 0 and payload["rendered"] == ["spec/TRACEABILITY.md"]
    assert (
        (tasklet_plan / "spec/TRACEABILITY.md")
        .read_text()
        .startswith("# Traceability — tasklet-alt")
    )
    p = tasklet_plan / "plans/phase-11-billing.md"
    p.write_text(p.read_text().replace("§10, R-011, ADR-011, ADR-013", "§10"))
    code, out, _ = pf_cli("trace", "--workspace", str(tasklet_plan), "--json")
    codes = {f["code"] for f in json.loads(out)["findings"]}
    assert code == 1 and codes == {
        "TRACE_R_NOT_PLANNED",
        "TRACE_ADR_UNUSED",
        "TRACE_PHASE_NO_REQUIREMENT",
    }


def test_global_adrs_need_no_phase(tasklet_plan: Path) -> None:
    p = tasklet_plan / "plans/phase-11-billing.md"
    p.write_text(p.read_text().replace("§10, R-011, ADR-011", "§10, R-011"))
    adr = next((tasklet_plan / "spec/decisions").glob("ADR-011-*.md"))
    assert {g.code for g in trace.gaps(tasklet_plan)} == {"TRACE_ADR_UNUSED"}
    adr.write_text(adr.read_text().replace("- Status: accepted", "- Status: global"))
    assert trace.gaps(tasklet_plan) == []
