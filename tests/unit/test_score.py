from __future__ import annotations

from pathlib import Path

import pytest

from pflib import config, score

W = score.weights()
T = score.Thresholds(build=6, defer=-4)
NAMES = list(score.SCORED_FIELDS)


def card(*vals: int) -> dict[str, int]:
    """core, freq, dep, diff, eng, infra, sec, ops, time, external."""
    return dict(zip(NAMES, vals, strict=True))


@pytest.mark.parametrize(
    "scores, stakes, prio, decision, rule",
    [
        # R2: a mature external service and real complexity → external, whatever the priority
        (card(1, 0, 1, 0, 3, 1, 3, 1, 2, 3), 0, -9, score.USE_EXTERNAL, "R2"),
        (card(3, 3, 3, 0, 2, 1, 3, 1, 2, 3), 0, 11, score.USE_EXTERNAL, "R2"),
        # …but external availability alone (simple to build) does not
        (card(3, 3, 1, 1, 1, 0, 0, 0, 1, 3), 0, 16, score.BUILD_NOW, "R4"),
        # R3: worth building but the hardest kind of engineering → simplified
        (card(3, 3, 2, 3, 3, 0, 0, 0, 1, 0), 0, 19, score.BUILD_SIMPLIFIED, "R3"),
        # R4: at the threshold
        (card(2, 2, 0, 1, 1, 1, 0, 1, 1, 1), 0, 6, score.BUILD_NOW, "R4"),
        # R5: just below build
        (card(1, 2, 0, 1, 1, 0, 0, 0, 1, 0), 0, 5, score.DEFER, "R5"),
        # R5 at the defer threshold, R6 just below it
        (card(1, 1, 0, 1, 2, 2, 0, 1, 2, 0), 0, -4, score.DEFER, "R5"),
        (card(1, 1, 0, 1, 2, 2, 1, 1, 2, 0), 0, -5, score.DROP, "R6"),
        # R1: dependency importance 3 is never deferred or dropped
        (card(0, 0, 3, 0, 3, 3, 3, 3, 3, 0), 0, -12, score.BUILD_SIMPLIFIED, "R1"),
        (card(0, 0, 3, 0, 1, 3, 3, 3, 3, 0), 0, -8, score.BUILD_NOW, "R1"),
        # table stakes add 2: 5 → 7 crosses the build threshold
        (card(1, 2, 0, 1, 1, 0, 0, 0, 1, 0), 2, 7, score.BUILD_NOW, "R4"),
        (card(1, 2, 0, 1, 1, 0, 0, 0, 1, 0), 1, 5, score.DEFER, "R5"),  # one competitor: no bonus
    ],
)
def test_decision_rules(
    scores: dict[str, int], stakes: int, prio: float, decision: str, rule: str
) -> None:
    p = score.priority(scores, W, stakes)
    assert p == prio
    got, why = score.decide(scores, p, T)
    assert (got, why.split()[0]) == (decision, rule)


def test_dependency_floor_holds_for_every_score_combination() -> None:
    import itertools

    for vals in itertools.product((0, 3), repeat=9):
        scores = card(*vals[:2], 3, *vals[2:])
        decision, _ = score.decide(scores, score.priority(scores, W), T)
        assert decision not in (score.DEFER, score.DROP), scores


def test_saml_example_from_the_reference() -> None:
    saml = card(1, 0, 0, 1, 3, 1, 3, 1, 3, 1)
    assert score.priority(saml, W) == -12
    assert score.decide(saml, -12, T)[0] == score.DROP


@pytest.mark.parametrize(
    "value, parsed",
    [("3 — every flow starts here", (3, "every flow starts here")), ("0 - none", (0, "none")),
     ("2 – en dash", (2, "en dash")), ("4 — too high", (None, "")), ("high", (None, "")),
     ("2", (None, "")), ("2 —", (None, ""))],
)  # fmt: skip
def test_parse_score(value: str, parsed: tuple[int | None, str]) -> None:
    assert score.parse_score(value) == parsed


def test_weights_and_thresholds_come_from_config(tasklet_scope: Path) -> None:
    config.write_config(tasklet_scope, {"scope.build_threshold": 20, "scope.weights.core_value": 1})
    assert score.thresholds(tasklet_scope) == score.Thresholds(20, -4)
    assert score.weights(tasklet_scope)["Core value"] == 1
    rows = {r.feature: r for r in score.evaluate(tasklet_scope)}
    # 13 < 20 would defer, but most features need tasks: the R1 floor keeps it (engineering 2)
    assert rows["F-001"].priority == 13 and rows["F-001"].decision == score.BUILD_SIMPLIFIED


def test_fixture_report_is_deterministic(tasklet_scope: Path) -> None:
    first = score.report(tasklet_scope)
    assert first == score.report(tasklet_scope)
    assert first["counts"] == {"BUILD NOW": 14, "BUILD SIMPLIFIED": 1, "USE EXTERNAL SERVICE": 3,
                               "DEFER": 11, "DROP": 2}  # fmt: skip
    (override,) = first["overrides"]
    assert override["feature"] == "F-009" and override["computed"] == score.DEFER
    assert override["decision"] == score.BUILD_SIMPLIFIED
    stakes = {r["feature"]: r["table_stakes"] for r in first["rows"] if r["table_stakes"]}
    assert stakes == {"F-001": 3, "F-008": 2, "F-014": 3}


def test_malformed_scores_yield_no_decision(tasklet_scope: Path) -> None:
    p = tasklet_scope / "spec/PARITY_MATRIX.md"
    p.write_text(
        p.read_text().replace(
            "- Core value: 1 — supports the core loop\n- User frequency: 0",
            "- Core value: high\n- User frequency: 0",
            1,
        )
    )
    (row,) = [r for r in score.evaluate(tasklet_scope) if r.priority is None]
    assert row.decision is None and "Core value" in row.rule
