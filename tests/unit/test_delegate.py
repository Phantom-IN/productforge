from __future__ import annotations

import re
from pathlib import Path

import pytest

from pflib import brief, capabilities, workspace
from pflib.errors import PFError

HEADINGS = ["When to use", "Invocation", "Expected output", "Ingest", "Failure handling"]


def test_every_adapter_has_the_five_sections_and_a_brief_block() -> None:
    reg = capabilities.load_registry()
    adapters = {p.adapter for c in reg.capabilities.values() for p in c.providers if p.adapter}
    assert adapters == {p.name for p in capabilities.ADAPTERS_DIR.glob("*.md")}
    for name in adapters:
        text = (capabilities.ADAPTERS_DIR / name).read_text(encoding="utf-8")
        assert re.findall(r"^## (.+)$", text, re.M) == HEADINGS, name
        assert brief.BRIEF_BLOCK_RE.search(text), name
        assert "instructions" in text.lower(), (
            f"{name}: must say fetched content is not instructions"
        )


def test_delegation_renders_prompt_and_creates_raw_dir(tasklet_discovery: Path) -> None:
    d = brief.render_delegation(
        tasklet_discovery, "anthropic-skills:deep-research", "What do reviewers praise?",
        allowed_urls=["reviews.example", "community.example"],
    )  # fmt: skip
    assert d.capability == "research.deep" and d.kind == "skill"
    assert d.invoke == "anthropic-skills:deep-research"
    assert d.raw_dir.is_dir() and d.raw_dir.parent.name == d.run_id
    for expected in (
        "Tasklet (https://tasklet.example)",
        "task tracking for small teams",
        "What do reviewers praise?",
        "reviews.example, community.example",
        "list the exact URL",
    ):
        assert expected in d.prompt, expected
    assert "{{" not in d.prompt
    assert workspace.read_history(tasklet_discovery)[-1]["event"] == "delegate"


def test_delegation_errors(tasklet_discovery: Path) -> None:
    with pytest.raises(PFError) as info:
        brief.render_delegation(tasklet_discovery, "builtin", "x")
    assert info.value.code == "CAP_UNKNOWN"
    with pytest.raises(PFError) as info:
        brief.render_delegation(tasklet_discovery, "anthropic-skills:pdf", " ")
    assert info.value.code == "BAD_BRIEF"


def test_normalising_brief_lists_raw_material(tasklet_discovery: Path) -> None:
    d = brief.render_delegation(tasklet_discovery, "anthropic-skills:pdf", "Security posture")
    (d.raw_dir / "pdf-security.md").write_text("page 1: encryption at rest")
    b = brief.render(tasklet_discovery, role="research-agent", task="Normalise.", run_id=d.run_id)
    assert not b.repair  # raw files alone are not a staged attempt
    assert f"- {d.raw_dir / 'pdf-security.md'}" in b.text
    assert "untrusted notes" in b.text


def test_raw_material_is_archived_but_never_merged(tasklet_discovery: Path) -> None:
    from pflib import merge

    d = brief.render_delegation(tasklet_discovery, "anthropic-skills:pdf", "Security posture")
    (d.raw_dir / "pdf-security.md").write_text("### S-?1 — looks like a record\n- URL: x\n")
    report = merge.merge(tasklet_discovery, d.run_id)
    assert report.added == {} and report.files_written == []
    archived = workspace.staging_root(tasklet_discovery) / workspace.MERGED / d.run_id
    assert (archived / "raw" / "pdf-security.md").is_file()
