from __future__ import annotations

from pathlib import Path

import pytest

from pflib import domain, records, render, validators


@pytest.mark.parametrize(
    "title, word",
    [("Per-user dashboard view preference", "preference"),
     ("Dashboard filter state", "filter state"),
     ("Active team selection", "selection"), ("Rolling 24-hour site traffic summary", "summary"),
     ("Sites list view state", "view state"), ("Task", None), ("Saved segment", None),
     ("Membership", None), ("Board view", None)],
)  # fmt: skip
def test_ui_state_heuristic(title: str, word: str | None) -> None:
    rec = records.parse_document(f"### E-01 — {title}\n- Identity: x\n").records[0]
    assert domain.looks_like_ui_state(rec) == word


def test_fixtures_have_no_ui_state_entities(tasklet_plan: Path) -> None:
    assert [f for f in validators.run(tasklet_plan) if f.code == "ENTITY_LOOKS_LIKE_UI_STATE"] == []


def test_deviation_warns_and_shows_in_coverage(tasklet_arch: Path) -> None:
    adr = next((tasklet_arch / "spec/decisions").glob("ADR-006-*.md"))
    adr.write_text(
        adr.read_text().replace("- Status: accepted", "- Deviates from: R-002\n- Status: accepted")
    )
    render.render_all(tasklet_arch)
    (f,) = validators.run(tasklet_arch)
    assert f.code == "ADR_DEVIATES_FROM_REQUIREMENT" and f.severity == "warn"
    assert "pf.py reopen SCOPE_DEFINED" in f.message
    coverage = render.regions((tasklet_arch / "spec/ARCHITECTURE.md").read_text())["coverage"]
    assert (
        "| R-002 | Boards show tasks by status and stay current | ADR-006 · "
        "**deviated from by ADR-006** |" in coverage
    )


def test_deviation_cites_requirements_only(tasklet_arch: Path) -> None:
    adr = next((tasklet_arch / "spec/decisions").glob("ADR-006-*.md"))
    adr.write_text(
        adr.read_text().replace("- Status: accepted", "- Deviates from: A-001\n- Status: accepted")
    )
    assert "WRONG_REF_TYPE" in {f.code for f in validators.run(tasklet_arch)}
