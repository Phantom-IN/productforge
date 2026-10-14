from __future__ import annotations

import re
from pathlib import Path

from pflib import records, research, scaffold

TEMPLATES = scaffold.TEMPLATES_DIR / "research"


def test_overview_coverage_lists_every_official_category() -> None:
    doc = records.parse_document((TEMPLATES / "product-overview.md").read_text())
    body = doc.section_text("Coverage") or ""
    listed = re.findall(r"^- ([a-z-]+): ", body, re.M)
    assert listed == list(research.COVERAGE_OFFICIAL)  # observed sessions are optional


def test_overview_has_the_planned_sections() -> None:
    doc = records.parse_document((TEMPLATES / "product-overview.md").read_text())
    assert [s.title for s in doc.sections if s.level == 2] == [
        "Product", "One-line description", "Target users", "Category", "Pricing model",
        "Major areas", "Recommended scope", "Accepted scope", "Coverage",
    ]  # fmt: skip


def test_init_scaffolds_discovery_templates_cleanly(tmp_path: Path) -> None:
    from pflib import validators

    ws, _ = scaffold.init_workspace("https://tasklet.example", out=str(tmp_path / "w"), scope="x")
    for rel in ("research/sources.md", "research/product-overview.md", "research/README.md"):
        text = (ws / rel).read_text()
        assert "{{" not in text and "Tasklet" in text, rel
    assert "## Records" in (ws / "research/sources.md").read_text()
    assert validators.run(ws) == []
