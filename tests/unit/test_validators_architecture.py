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
    edit(tasklet_arch, "- Satisfies: R-011", "- Satisfies: R-009", rel=adr(tasklet_arch, 13))
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


# ------------------------------------------------------------------ UNDECIDED_CHOICE


def test_undecided_phrase_in_an_adr_is_an_error(tasklet_arch: Path) -> None:
    edit(
        tasklet_arch,
        "Delivery depends on a verified sending domain",
        "the library choice is open",
        rel=adr(tasklet_arch, 14),
    )
    found = [f for f in validators.run(tasklet_arch) if f.code == "UNDECIDED_CHOICE"]
    assert len(found) == 1 and found[0].severity == "error"
    assert "library choice" in found[0].message and "line" in found[0].message


def test_undecided_phrases_match_whole_phrases_case_insensitively(tasklet_arch: Path) -> None:
    edit(
        tasklet_arch, "Fees scale with revenue", "Vendor Is Open for now", rel=adr(tasklet_arch, 13)
    )
    assert "UNDECIDED_CHOICE" in codes(tasklet_arch)
    edit(tasklet_arch, "Vendor Is Open for now", "the TBDs are gone", rel=adr(tasklet_arch, 13))
    assert "UNDECIDED_CHOICE" not in codes(tasklet_arch)


def test_undecided_phrase_in_a_phase_file_and_html_comments(tasklet_plan: Path) -> None:
    rel = "plans/phase-02-sign-in.md"
    edit(
        tasklet_plan,
        "## Open questions / risks\n\n- None.",
        "## Open questions / risks\n\n- The library choice is open.",
        rel=rel,
    )
    found = [f for f in validators.run(tasklet_plan) if f.code == "UNDECIDED_CHOICE"]
    assert [f.artifact for f in found] == [rel]
    edit(tasklet_plan, "- The library choice is open.", "<!-- library choice -->\n- None.", rel=rel)
    assert "UNDECIDED_CHOICE" not in codes(tasklet_plan)


def test_undecided_choice_is_ignored_before_architecture_locked(tasklet_arch: Path) -> None:
    import json

    edit(
        tasklet_arch,
        "Delivery depends on a verified sending domain",
        "TBD",
        rel=adr(tasklet_arch, 14),
    )
    assert "UNDECIDED_CHOICE" in codes(tasklet_arch)
    st = tasklet_arch / ".productforge/state.json"
    data = json.loads(st.read_text())
    data["state"] = "SCOPE_DEFINED"
    st.write_text(json.dumps(data))
    assert "UNDECIDED_CHOICE" not in codes(tasklet_arch)


def test_undecided_phrases_are_configurable(tasklet_arch: Path) -> None:
    from pflib import config

    edit(
        tasklet_arch,
        "Delivery depends on a verified sending domain",
        "pick one soon",
        rel=adr(tasklet_arch, 14),
    )
    assert "UNDECIDED_CHOICE" not in codes(tasklet_arch)
    config.write_config(tasklet_arch, {"quality.undecided_phrases": ["pick one soon"]})
    assert "UNDECIDED_CHOICE" in codes(tasklet_arch)
