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


# ------------------------------------------------------------- cross-phase contracts (v3)


def _phase(
    n: str, deps: str, context: str = "Builds it.", tasks: str = "", questions: str = "- None."
) -> tuple[str, str]:
    tasks = tasks or f"1. `apps/api/src/p{n}/`: the work."
    return f"plans/phase-{n}-x.md", (
        f"# Phase {n} — X{n}\n\n**Status:** Not started\n**Depends on:** {deps}\n**Goal:** g\n\n"
        f"## Context\n\n{context}\n\n## Scope\n\n**In:**\n- a\n\n**Out / deferred:**\n- b\n\n"
        f"## Tasks\n\n{tasks}\n\n## Data & schema changes\n\n- n\n\n## API / contracts\n\n- n\n\n"
        "## Acceptance criteria\n\n- [ ] a\n- [ ] b\n- [ ] c\n\n## Test plan\n\n- t\n\n"
        f"## References\n\n- x\n\n## Open questions / risks\n\n{questions}\n\n"
        "## Definition of done\n\n- [ ] d\n"
    )


def contract_codes(*phases: tuple[str, str], undecided: tuple[str, ...] = ()) -> list[str]:
    ps = phaselint.PlanSet(phases=dict(phases), undecided_phrases=undecided, min_acceptance=1)
    return sorted(i.code for i in phaselint.lint(ps).issues if i.code.startswith("PHASE_"))


CHAIN = [_phase("00", "none"), _phase("01", "00"), _phase("02", "01")]


def test_later_phase_use_is_an_error_and_a_dependency_clears_it() -> None:
    sentence = "It uses `ensurePdf` from phase 02."
    bad = [CHAIN[0], _phase("01", "00", sentence), CHAIN[2]]
    assert contract_codes(*bad) == ["PHASE_USES_LATER_PHASE"]
    ok = [CHAIN[0], CHAIN[1], _phase("02", "01", "It uses `ensurePdf` from phase 01.")]
    assert contract_codes(*ok) == []


@pytest.mark.parametrize(
    "text",
    [
        "from phase 02", "created in phase 02", "built in phase 02", "added by phase 02",
        "phase 02's helper", "Phase 02’s helper",
    ],
)  # fmt: skip
def test_later_phase_patterns(text: str) -> None:
    phases = [CHAIN[0], _phase("01", "00", f"Uses it {text}."), CHAIN[2]]
    assert contract_codes(*phases) == ["PHASE_USES_LATER_PHASE"]


@pytest.mark.parametrize(
    "text",
    [
        "Phase 02 adds the helper.",
        "a later phase wires it.",
        "deferred to phase 02.",
        "phase 02's worker job calls them directly.",
        "e2e runs in its own job from phase 02.",
        "the services it needs (PostgreSQL from phase 02 onward).",
        "Attached becomes Used when phase 02's webhook fires.",
        "the full-stack run is phase 02's CI job.",
        "Each adapter arrives with the phase that uses it: Resend is built in phase 02.",
    ],
)
def test_allowed_phrasings_are_clean(text: str) -> None:
    assert contract_codes(CHAIN[0], _phase("01", "00", text), CHAIN[2]) == []


def test_scope_out_and_fenced_lines_are_ignored() -> None:
    p = _phase("01", "00")
    body = p[1].replace("- b\n", "- reuse from phase 02\n", 1)
    body = body.replace("Builds it.", "```\nfrom phase 02\n```", 1)
    assert contract_codes(CHAIN[0], (p[0], body), CHAIN[2]) == []


def test_earlier_non_dependency_warns_and_the_closure_has_two_hops() -> None:
    phases = [
        CHAIN[0],
        _phase("01", "00"),
        _phase("02", "00"),
        _phase("03", "02", "Calls the helper from phase 01."),
    ]
    assert contract_codes(*phases) == ["PHASE_USES_NON_DEP"]
    chain = [*CHAIN, _phase("03", "02", "Calls the helper from phase 00.")]
    assert contract_codes(*chain) == []  # 03 → 02 → 01 → 00
    res = phaselint.lint(phaselint.PlanSet(phases=dict(chain), min_acceptance=1))
    assert phaselint.closure(res.phases)["03"] == {"00", "01", "02"}


def test_path_creator_outside_closure_warns() -> None:
    shared = "1. `apps/api/src/shared/registry.ts`: add an entry."
    phases = [
        _phase("00", "none"),
        _phase("01", "00", tasks="1. `apps/api/src/shared/registry.ts`: create it."),
        _phase("02", "00", tasks=shared),
    ]
    assert contract_codes(*phases) == ["PHASE_PATH_CREATOR_NOT_DEP"]
    phases[2] = _phase("02", "01", tasks=shared)
    assert contract_codes(*phases) == []


def test_root_files_and_patterns_are_not_creator_paths() -> None:
    task = "1. `package.json`, `Makefile`, `infra/Makefile` and `docs/**/*.md`: update."
    phases = [_phase("00", "none", tasks=task), _phase("01", "none", tasks=task)]
    assert contract_codes(*phases) == []


@pytest.mark.parametrize(
    "bullet",
    [
        "- Ask the user which S3 library to use.",
        "- We must choose between two queues.",
        "- Decide the retry budget.",
        "- Pick a region later.",
        "- The vendor is TBD.",
    ],
)
def test_open_questions_that_ask_for_a_choice(bullet: str) -> None:
    code = contract_codes(_phase("00", "none", questions=bullet), undecided=("TBD",))
    assert code == ["PHASE_OPEN_DECISION"]


def test_recorded_risks_are_clean() -> None:
    risk = "- The vendor's sandbox rate limit may slow the e2e run (ADR-004 accepts it)."
    assert contract_codes(_phase("00", "none", questions=risk), undecided=("TBD",)) == []
    assert contract_codes(_phase("00", "none", questions="- None.")) == []


def test_orchestrator_prompt_is_a_root_document(tasklet_plan: Path) -> None:
    assert "ORCHESTRATOR_PROMPT.md" in phaselint.ROOT_HEADINGS
    p = tasklet_plan / "ORCHESTRATOR_PROMPT.md"
    assert "{{" not in p.read_text()
    p.write_text(p.read_text().replace("## 5. Token discipline", "## 5. Thrift"))
    (issue,) = plans.root_doc_issues(tasklet_plan)
    assert issue.rel == "ORCHESTRATOR_PROMPT.md" and "Token discipline" in issue.message
    p.unlink()
    (issue,) = plans.root_doc_issues(tasklet_plan)
    assert issue.message == "file is missing"


def test_orchestrator_template_uses_only_placeholder_tokens() -> None:
    from pathlib import Path as P

    text = (
        P(phaselint.__file__).resolve().parents[2] / "templates/project/ORCHESTRATOR_PROMPT.md"
    ).read_text()
    for needle in ("git init -b main", "git worktree add", "ORCHESTRATION_LOG.md", "opus",
                   "haiku", "--no-ff", "renumber", "{{our_name}}", "{{ci_command}}"):  # fmt: skip
        assert needle in text, needle


def test_a_use_verb_before_the_reference_is_needed_and_paths_do_not_end_the_clause() -> None:
    hit = "It reads `pkg/registry.ts` from phase 02."
    assert contract_codes(CHAIN[0], _phase("01", "00", hit), CHAIN[2]) == ["PHASE_USES_LATER_PHASE"]
    note = "The helper is exported. Phase 02's job uses it."
    assert contract_codes(CHAIN[0], _phase("01", "00", note), CHAIN[2]) == []
