from __future__ import annotations

from pathlib import Path

import pytest

from pflib import phaselint, plans, validators


def lint_codes(ws: Path) -> list[str]:
    return sorted({i.code for i in plans.lint(ws).issues + plans.root_doc_issues(ws)})


def test_fixture_plan_is_clean(tasklet_plan: Path) -> None:
    result = plans.lint(tasklet_plan)
    assert result.issues == [] and plans.root_doc_issues(tasklet_plan) == []
    assert [p["number"] for p in result.summary()][:3] == ["00", "01", "02"]
    assert result.summary()[12]["depends_on"] == ["07", "09", "10", "11"]


@pytest.mark.parametrize(
    "line, pos_text, idea",
    [
        ("IDEA.md §11 (create-issue example), §33 (UX Analyst)", "§33", True),
        ("examples (D-041 from IDEA §18), status values (§6.3)", "§6.3", False),
        ("IMPLEMENTATION_PLAN.md §16 (IDEA §27–§31). Template (§16.2)", "§16.2", False),
        ("IMPLEMENTATION_PLAN §12.4, IDEA §12–§14", "§14", True),
        ("plain §7 reference", "§7", False),
    ],
)
def test_section_references_belong_to_the_last_named_document(
    line: str, pos_text: str, idea: bool
) -> None:
    assert phaselint.cites_idea(line, line.rindex(pos_text)) is idea


@pytest.mark.parametrize(
    "line, paths",
    [
        ("1. `apps/api/src/tasks/`: endpoints", ["apps/api/src/tasks/"]),
        ("2. `pf.py advance --to X`: …", ["pf.py"]),
        ("3. update SKILL.md and `Makefile`", ["Makefile", "SKILL.md"]),
        ("4. `MVP/Decision/Score` columns", []),
        ("5. `n/m conditions`", []),
        ("6. `R/A` refs", []),
        ("7. `**/.productforge/staging/`", ["**/.productforge/staging/"]),
    ],
)
def test_path_tokens(line: str, paths: list[str]) -> None:
    assert sorted(phaselint.path_tokens(line)) == sorted(paths)


def test_numbered_items_under_a_section_resolve(tasklet_plan: Path) -> None:
    plan = "## 3. Stack\n\n1. one\n2. two\n\n### 3.5 Sub\n"
    heads, items = phaselint.section_numbers(plan)
    assert heads == {"3", "3.5"} and items == {"3": {"1", "2"}}


def test_golden_rules_must_match_invariants(tasklet_plan: Path) -> None:
    p = tasklet_plan / "CLAUDE.md"
    p.write_text(
        p.read_text().replace("7. **Files are served only after a policy check**", "**x**")
    )
    issues = plans.root_doc_issues(tasklet_plan)
    assert [i.code for i in issues] == ["ROOTDOC_SECTION_MISSING"]
    assert "6 rules but there are 7 invariants" in issues[0].message


def test_plan_sections_must_be_exact(tasklet_plan: Path) -> None:
    p = tasklet_plan / "IMPLEMENTATION_PLAN.md"
    p.write_text(p.read_text().replace("## 12. Realtime behaviour", "## 12. Realtime"))
    (issue,) = plans.root_doc_issues(tasklet_plan)
    assert "12. Realtime behaviour" in issue.message


def test_lint_findings_are_validator_findings(tasklet_plan: Path) -> None:
    p = tasklet_plan / "plans/phase-07-board-and-polling.md"
    p.write_text(p.read_text().replace("**Depends on:** 06", "**Depends on:** 06, 08"))
    found = [f for f in validators.run(tasklet_plan) if f.code.startswith("PHASE_")]
    assert [(f.code, f.artifact) for f in found] == [
        ("PHASE_DEP_FORWARD", "plans/phase-07-board-and-polling.md")
    ]
    assert lint_codes(tasklet_plan) == ["PHASE_DEP_FORWARD"]


def test_lint_phases_cli(pf_cli, tasklet_plan: Path) -> None:  # type: ignore[no-untyped-def]
    import json

    code, out, _ = pf_cli("lint-phases", "--workspace", str(tasklet_plan), "--json")
    payload = json.loads(out)
    assert code == 0 and payload["errors"] == 0 and len(payload["phases"]) == 13
    (tasklet_plan / "plans/phase-05-projects.md").write_text("# not a phase\n")
    code, out, _ = pf_cli("lint-phases", "--workspace", str(tasklet_plan), "--json")
    assert code == 1 and "PHASE_HEADER_FIELDS" in {f["code"] for f in json.loads(out)["findings"]}


def test_before_finalize_nothing_is_linted(tasklet_arch: Path) -> None:
    assert plans.lint(tasklet_arch).issues == [] and plans.root_doc_issues(tasklet_arch) == []
