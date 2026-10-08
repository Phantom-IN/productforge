from __future__ import annotations

import re
from pathlib import Path

import pytest
from conftest import INVALID, TASKLET, apply_overlay

from pflib import validators

REFERENCE = Path(__file__).resolve().parents[2] / "skills/productforge/references/record-format.md"
CASES = sorted(INVALID.glob("*.md"))


def codes(ws: Path) -> list[str]:
    return [f.code for f in validators.run(ws)]


@pytest.mark.parametrize("snapshot", sorted(p for p in TASKLET.iterdir() if p.is_dir()))
def test_fixture_snapshots_have_no_findings(snapshot: Path) -> None:
    assert [f.to_dict() for f in validators.run(snapshot)] == []


@pytest.mark.parametrize("case", CASES, ids=lambda p: p.stem)
def test_each_invalid_case_yields_exactly_its_code(tasklet_discovery: Path, case: Path) -> None:
    expected = apply_overlay(tasklet_discovery, case)
    assert expected == case.stem
    found = validators.run(tasklet_discovery)
    assert found, f"{case.name} produced no findings"
    assert {f.code for f in found} == {expected}, [f.to_dict() for f in found]
    assert all(f.severity == validators.CODES[expected][0] for f in found)


def test_every_declared_code_has_an_invalid_case_and_vice_versa() -> None:
    assert {c.stem for c in CASES} == set(validators.CODES)


def test_reference_documents_exactly_the_declared_codes() -> None:
    text = REFERENCE.read_text(encoding="utf-8")
    section = text.split("## Validator finding codes", 1)[1].split("\n## ", 1)[0]
    documented = set(re.findall(r"^\| `([A-Z_]+)` \|", section, re.M))
    assert documented == set(validators.CODES)


def test_findings_carry_artifact_and_record(tasklet_discovery: Path) -> None:
    apply_overlay(tasklet_discovery, INVALID / "DANGLING_REF.md")
    (f,) = validators.run(tasklet_discovery)
    assert f.artifact == "research/DISCOVERY_LEDGER.md" and f.record_id == "D-100"
    assert "S-099" in f.message


def test_stage_and_artifact_filters(tasklet_discovery: Path) -> None:
    apply_overlay(tasklet_discovery, INVALID / "BAD_TIER.md")
    assert codes(tasklet_discovery) == ["BAD_TIER"]
    assert validators.run(tasklet_discovery, stage="PRODUCT_MODEL") == []
    assert [f.code for f in validators.run(tasklet_discovery, stage="DISCOVERY")] == ["BAD_TIER"]
    assert validators.run(tasklet_discovery, artifact="research/DISCOVERY_LEDGER.md") == []


def test_cross_file_duplicate_ids(tasklet_discovery: Path) -> None:
    wf = tasklet_discovery / "research/workflows"
    wf.mkdir()
    body = "### W-001 — Create task\n- Actor: Member\n"
    (wf / "W-001-create-task.md").write_text(body)
    (wf / "W-001-copy.md").write_text(body)
    assert "DUPLICATE_ID" in codes(tasklet_discovery)


def test_parse_error_does_not_hide_the_rest_of_the_file(tasklet_discovery: Path) -> None:
    apply_overlay(tasklet_discovery, INVALID / "PARSE_ERROR.md")
    ctx = validators.Context.load(tasklet_discovery)
    assert ctx.get("D-018") is not None  # records after the bad one are still indexed
