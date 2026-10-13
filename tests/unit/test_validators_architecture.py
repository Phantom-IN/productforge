from __future__ import annotations

from pathlib import Path

from pflib import architecture, validators

ARCH = "spec/ARCHITECTURE.md"


def codes(ws: Path) -> list[str]:
    return [f.code for f in validators.run(ws)]


def edit(ws: Path, old: str, new: str, rel: str = ARCH) -> None:
    p = ws / rel
    text = p.read_text()
    assert old in text, old
    p.write_text(text.replace(old, new, 1))


def adr(ws: Path, n: int) -> str:
    return next(p for p in (ws / "spec/decisions").iterdir() if p.name.startswith(f"ADR-{n:03d}-")
                ).relative_to(ws).as_posix()  # fmt: skip


def test_fixture_is_clean_and_fully_covered(tasklet_arch: Path) -> None:
    assert validators.run(tasklet_arch) == []
    cov = architecture.coverage(tasklet_arch)
    assert cov.unaddressed == cov.unproposed == cov.multi_proposed == cov.topics_missing == []
    assert cov.by_requirement["R-005"] == ["ADR-010", "convention"]


def test_preferences_appear_in_the_adrs(tasklet_arch: Path) -> None:
    import json

    prefs = json.loads((tasklet_arch / ".productforge/config.json").read_text())
    text = "".join(p.read_text() for p in (tasklet_arch / "spec/decisions").iterdir())
    assert all(pref in text for pref in prefs["architecture.preferences"])


def test_not_applicable_topic_counts_as_covered(tasklet_arch: Path) -> None:
    edit(tasklet_arch, "- search: global search is deferred in V1 (SC-019)\n", "")
    assert codes(tasklet_arch) == ["ADR_TOPIC_MISSING"]


def test_convention_line_addresses_a_requirement(tasklet_arch: Path) -> None:
    edit(tasklet_arch, "- Satisfies: R-011", "- Satisfies: R-009", rel=adr(tasklet_arch, 11))
    assert "REQUIREMENT_UNADDRESSED" in codes(tasklet_arch)
    edit(
        tasklet_arch,
        "- R-005: comments",
        "- R-011: billing follows the payment provider\n- R-005: comments",
    )
    assert "REQUIREMENT_UNADDRESSED" not in codes(tasklet_arch)


def test_two_proposals_for_one_inference(tasklet_arch: Path) -> None:
    p = tasklet_arch / "research/architecture-inference.md"
    p.write_text(p.read_text() + "\n### AP-100 — Second proposal for A-001\n- Inference: A-001\n"
                 "- Proposed implementation: WebSockets\n- Decision: ADR-006\n")  # fmt: skip
    found = [f for f in validators.run(tasklet_arch) if f.code == "INFERENCE_UNPROPOSED"]
    assert len(found) == 1 and "several proposals: A-001" in found[0].message


def test_superseded_target_reference_types(tasklet_arch: Path) -> None:
    edit(tasklet_arch, "- Satisfies: R-011", "- Satisfies: F-023", rel=adr(tasklet_arch, 11))
    assert "WRONG_REF_TYPE" in codes(tasklet_arch)


def test_enforcement_kinds() -> None:
    assert architecture.enforcement_kind("db-constraint — RLS") == "db-constraint"
    assert architecture.enforcement_kind("Tests cover it") is None  # must lead with the mechanism
    assert architecture.alternatives("a; b ;; c") == ["a", "b", "c"]


def test_before_design_nothing_is_required(tasklet_scope: Path) -> None:
    assert validators.run(tasklet_scope) == []
