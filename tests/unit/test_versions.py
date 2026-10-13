from __future__ import annotations

import json
import re
from pathlib import Path

from pflib import __version__

ROOT = Path(__file__).resolve().parents[2]


def test_versions_agree() -> None:
    plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
    market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    (entry,) = [p for p in market["plugins"] if p["name"] == "productforge"]
    assert __version__ == plugin["version"] == entry["version"] == "1.0.0"


def test_changelog_has_the_release() -> None:
    text = (ROOT / "CHANGELOG.md").read_text()
    assert re.search(rf"^## \[{re.escape(__version__)}\] — \d{{4}}-\d{{2}}-\d{{2}}$", text, re.M)


def test_example_is_the_phase_plan_fixture() -> None:
    example = ROOT / "examples/tasklet"
    fixture = ROOT / "tests/fixtures/workspaces/tasklet/PHASE_PLAN_READY"
    files = sorted(p.relative_to(fixture).as_posix() for p in fixture.rglob("*") if p.is_file())
    for rel in files:
        assert (example / rel).read_text() == (fixture / rel).read_text(), rel
