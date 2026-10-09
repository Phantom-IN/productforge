from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import REPO_ROOT, TASKLET

from pflib import config, gates


def failing(ws: Path) -> list[str]:
    return gates.evaluate(ws, "DISCOVERY").failing()


def test_passing_fixture_passes_every_condition() -> None:
    report = gates.evaluate(TASKLET / "DISCOVERY", "DISCOVERY")
    assert report.passed, [r.to_dict() for r in report.results if not r.passed]
    details = {r.id: r.detail for r in report.results}
    assert details["G-DISC-MIN-CLAIMS"].startswith("42 active claims")
    assert "4 explained by unknowns" in details["G-DISC-COVERAGE"]


def test_failing_fixture_fails_exactly_tier1_and_claims() -> None:
    assert failing(TASKLET / "DISCOVERY_FAILING") == ["G-DISC-TIER1", "G-DISC-MIN-CLAIMS"]


@pytest.fixture
def ws(tasklet_discovery: Path) -> Path:
    return tasklet_discovery


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new))


def test_coverage_needs_a_source_or_an_existing_unknown(ws: Path) -> None:
    overview = ws / "research/product-overview.md"
    edit(overview, "- enterprise: U-005", "- enterprise: —")
    assert failing(ws) == ["G-DISC-COVERAGE"]
    edit(overview, "- enterprise: —", "- enterprise: U-099")  # a dangling unknown is not enough
    assert "G-DISC-COVERAGE" in failing(ws)


def test_overview_placeholders_fail(ws: Path) -> None:
    edit(ws / "research/product-overview.md", "Task tracking for small teams (S-007).",
         "_Not researched yet._")  # fmt: skip
    assert failing(ws) == ["G-DISC-OVERVIEW"]
    (ws / "research/product-overview.md").unlink()
    assert "G-DISC-OVERVIEW" in failing(ws) and "G-DISC-COVERAGE" in failing(ws)


def test_surfaces_and_thresholds(ws: Path) -> None:
    surfaces = ws / "research/product-surfaces.md"
    surfaces.write_text(surfaces.read_text().split("\n### PS-01")[0])
    assert failing(ws) == ["G-DISC-SURFACES"]
    shutil.copy(TASKLET / "DISCOVERY/research/product-surfaces.md", surfaces)
    config.write_config(ws, {"research.min_sources_gate": 21, "research.min_claims_gate": 43})
    assert failing(ws) == ["G-DISC-MIN-SOURCES", "G-DISC-MIN-CLAIMS"]


def test_advance_through_the_real_gate(
    pf_cli: Callable[..., tuple[int, str, str]], ws: Path
) -> None:
    code, out, err = pf_cli(
        "advance", "--to", "PRODUCT_MODEL", "--confirmed", "--workspace", str(ws), "--json"
    )
    assert code == 0, (out, err)
    payload = json.loads(out)
    assert payload["transitioned"] and payload["open_stage"] == "PRODUCT_MODEL"
    assert payload["locked_records"] == 20 + 44 + 8 + 7  # S + D + U + PS
    state = json.loads((ws / ".productforge/state.json").read_text())
    assert state["state"] == "PRODUCT_MODEL" and "DISCOVERY" in state["locks"]


def test_committed_fixtures_match_the_generator() -> None:
    proc = subprocess.run([sys.executable, str(REPO_ROOT / "tests/fixtures/build_tasklet.py"),
                           "--check"], capture_output=True, text=True)  # fmt: skip
    assert proc.returncode == 0, proc.stdout
