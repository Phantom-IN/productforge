from __future__ import annotations

from pathlib import Path

import pytest

from pflib import validators

CO = "research/COMPETITORS.md"


def codes(ws: Path) -> list[str]:
    return [f.code for f in validators.run(ws)]


def edit(ws: Path, old: str, new: str, rel: str = CO) -> None:
    p = ws / rel
    text = p.read_text()
    assert old in text, old
    p.write_text(text.replace(old, new, 1))


def test_fixture_competitors_are_clean(tasklet_product_model: Path) -> None:
    assert validators.run(tasklet_product_model) == []


@pytest.mark.parametrize(
    "old, new, code",
    [
        ("- Competitors: C-01, C-02, C-03\n", "- Competitors: C-01\n",
         "TABLE_STAKES_UNDERSUPPORTED"),
        ("- Feature: F-030\n", "- Feature: F-030, F-025\n", "BAD_FEATURE_SIGNAL"),
        ("- Feature: Time tracking\n", "- Feature: F-001\n", "BAD_FEATURE_SIGNAL"),
        ("- Signal: rare\n- Competitors: C-03\n", "- Signal: rare\n- Competitors: C-01, C-03\n",
         "BAD_FEATURE_SIGNAL"),
        ("- Signal: differentiator", "- Signal: hot", "BAD_ENUM"),
        ("- Competitors: C-02\n", "- Competitors: C-09\n", "DANGLING_REF"),
        ("- Competitors: C-02\n", "- Competitors: F-019\n", "WRONG_REF_TYPE"),
        ("(S-026)", "(S-025)", "COMPLAINT_SOURCE_TIER"),
        ("(S-026)", "", "COMPLAINT_SOURCE_TIER"),
    ],
)  # fmt: skip
def test_competitor_findings(tasklet_product_model: Path, old: str, new: str, code: str) -> None:
    edit(tasklet_product_model, old, new)
    assert code in codes(tasklet_product_model)


def test_no_complaints_found_is_fine(tasklet_product_model: Path) -> None:
    edit(tasklet_product_model, "Mobile app lags behind the web app (S-026)", "None found")
    assert validators.run(tasklet_product_model) == []


def test_competitor_sources_never_support_target_claims(tasklet_product_model: Path) -> None:
    edit(tasklet_product_model, "- Evidence: D-036\n", "- Evidence: D-036, S-025\n",
         rel="research/architecture-inference.md")  # fmt: skip
    found = [f for f in validators.run(tasklet_product_model)
             if f.code == "COMPETITOR_SOURCE_AS_EVIDENCE"]  # fmt: skip
    assert [(f.record_id, "S-025" in f.message) for f in found] == [("A-002", True)]


def test_competitor_area_must_name_a_competitor(tasklet_product_model: Path) -> None:
    old = "- Relevant area: competitor:C-03\n- Published: unknown"
    edit(tasklet_product_model, old, old.replace("C-03", "C-07"), rel="research/sources.md")
    assert "DANGLING_REF" in codes(tasklet_product_model)
