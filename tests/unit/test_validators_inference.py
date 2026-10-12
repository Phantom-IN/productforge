from __future__ import annotations

from pathlib import Path

import pytest

from pflib import tech_terms, validators

AI = "research/architecture-inference.md"


def codes(ws: Path) -> list[str]:
    return [f.code for f in validators.run(ws)]


def edit(ws: Path, old: str, new: str, rel: str = AI) -> None:
    p = ws / rel
    text = p.read_text()
    assert old in text, old
    p.write_text(text.replace(old, new, 1))


def test_fixture_inferences_are_clean(tasklet_product_model: Path) -> None:
    assert validators.run(tasklet_product_model) == []


def test_target_technology_needs_a_confirmed_tier2_claim(tasklet_product_model: Path) -> None:
    ws = tasklet_product_model
    # A-001 cites D-007 (CONFIRMED; S-009 and S-015 are Tier 2): a stated mechanism is allowed
    edit(ws, "- Target implementation: UNKNOWN\n- Our requirement: Task changes",
         "- Target implementation: Persistent connections, per the engineering blog\n"
         "- Our requirement: Task changes")  # fmt: skip
    assert "TARGET_IMPL_UNSUPPORTED" not in codes(ws)
    # …but not when the only evidence is a PROBABLE claim (D-006: a Tier 3 review)
    edit(ws, "- Evidence: D-007\n", "- Evidence: D-006\n")
    assert "TARGET_IMPL_UNSUPPORTED" in codes(ws)


def test_unknown_with_a_note_is_fine(tasklet_product_model: Path) -> None:
    old = "- Target implementation: UNKNOWN\n- Our requirement: Search"
    edit(tasklet_product_model, old, old.replace("UNKNOWN", "UNKNOWN (not documented)"))
    assert validators.run(tasklet_product_model) == []


@pytest.mark.parametrize(
    "old, new, code",
    [
        ("- Our requirement: Task changes must be visible to other connected clients within 2 s",
         "- Our requirement: Task changes should feel instant", "REQUIREMENT_NOT_MEASURABLE"),
        ("- Engineering implication: The server pushes changes to connected clients",
         "- Engineering implication: The server pushes changes over WebSockets",
         "TECH_ASSERTION_IN_OBSERVATION"),
        ("- Area: realtime", "- Area: magic", "BAD_ENUM"),
        ("- Derived from: W-001, W-007, F-009, D-007", "- Derived from: W-001, S-009",
         "WRONG_REF_TYPE"),
        ("- Our requirement: Task changes must be visible to other connected clients within 2 s\n",
         "- Our requirement: Task changes must be visible to other connected clients within 2 s\n"
         "- Proposed implementation: a fan-out service\n", "FIELD_NOT_YET_ALLOWED"),
    ],
)  # fmt: skip
def test_inference_findings(tasklet_product_model: Path, old: str, new: str, code: str) -> None:
    edit(tasklet_product_model, old, new)
    assert code in codes(tasklet_product_model)


def test_tech_terms_are_warnings_only(tasklet_product_model: Path) -> None:
    old = "- Observation: One search box finds both tasks and projects"
    edit(tasklet_product_model, old, old.replace("box", "box (Elasticsearch, per a forum)"))
    found = validators.run(tasklet_product_model)
    assert [(f.code, f.severity, f.record_id) for f in found] == [
        ("TECH_ASSERTION_IN_OBSERVATION", "warn", "A-002")
    ]


def test_a_technology_the_evidence_states_is_not_flagged(tasklet_product_model: Path) -> None:
    ws = tasklet_product_model
    edit(ws, "- Claim: The system needs near-realtime propagation of task changes to connected "
         "clients.", "- Claim: The engineering blog says task changes reach clients over "
         "WebSockets.", rel="research/DISCOVERY_LEDGER.md")  # fmt: skip
    edit(ws, "- Evidence: D-007\n", "- Evidence: D-007, D-008\n")
    edit(ws, "- Engineering implication: The server pushes changes to connected clients",
         "- Engineering implication: The server pushes changes over WebSockets")  # fmt: skip
    assert "TECH_ASSERTION_IN_OBSERVATION" not in codes(ws)


def test_tech_term_matching() -> None:
    assert tech_terms.find("Pushes over WebSockets; stored in Postgres; files on S3") == [
        "websockets", "postgres", "s3",
    ]  # fmt: skip
    assert tech_terms.find("Users react to events; a lambda-like step; side rails") == []


def test_integration_direction_is_a_closed_set(tasklet_product_model: Path) -> None:
    edit(tasklet_product_model, "- Direction: inbound", "- Direction: both ways",
         rel="spec/INTEGRATIONS.md")  # fmt: skip
    assert "BAD_ENUM" in codes(tasklet_product_model)
