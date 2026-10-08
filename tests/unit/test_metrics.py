from __future__ import annotations

from pathlib import Path

from pflib import ids, metrics


def test_fresh_workspace_counts_are_zero(new_ws: Path) -> None:
    counts = metrics.counts(new_ws)
    assert set(counts) == set(ids.PREFIXES) and not any(counts.values())
    assert metrics.confidence_breakdown(new_ws) == {
        "CONFIRMED": 0,
        "PROBABLE": 0,
        "INFERRED": 0,
        "UNKNOWN": 0,
    }
    assert metrics.summary(new_ws)["domains"] == 0


def test_counts_confidence_and_domains(new_ws: Path) -> None:
    (new_ws / "research/DISCOVERY_LEDGER.md").write_text(
        "### D-001 — a\n- Confidence: CONFIRMED\n\n### D-002 — b\n- Confidence: probable\n\n"
        "### D-003 — c\n- Confidence: CONFIRMED\n"
    )
    (new_ws / "research/FEATURE_MATRIX.md").write_text(
        "### F-001 — x\n- Domain: Tasks\n\n### F-002 — y\n- Domain: Tasks\n\n"
        "### F-003 — z\n- Domain: Projects\n"
    )
    assert metrics.counts(new_ws)["D"] == 3
    assert metrics.confidence_breakdown(new_ws)["CONFIRMED"] == 2
    assert metrics.confidence_breakdown(new_ws)["PROBABLE"] == 1
    summary = metrics.summary(new_ws)
    assert summary["claims"] == 3 and summary["features"] == 3 and summary["domains"] == 2
