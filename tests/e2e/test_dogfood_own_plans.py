"""ProductForge's own phase plans must satisfy ProductForge's phase lint (§16.4)."""

from __future__ import annotations

from pathlib import Path

from pflib import phaselint, repotree

ROOT = Path(__file__).resolve().parents[2]
# ProductForge's plans also name workspace artifacts (research/, spec/ …) and the git-ignored
# dogfood working directory; those are not part of this repository's tree.
WORKSPACE_DIRS = ("research/", "spec/", "plans/", "staging/", ".productforge/", ".dogfood/")


def own_plan_set(folder: str = "v1") -> phaselint.PlanSet:
    plan = (ROOT / "IMPLEMENTATION_PLAN.md").read_text(encoding="utf-8")
    section = plan.split("## 4. Repository structure", 1)[1].split("\n## ", 1)[0]
    block = repotree.fenced_block(section)
    assert block is not None
    return phaselint.PlanSet(
        phases={
            p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted((ROOT / "plans" / folder).glob("phase-*.md"))
        },  # fmt: skip
        plan_text=plan,
        readme_text=(ROOT / "plans" / folder / "README.md").read_text(encoding="utf-8"),
        readme_rel=f"plans/{folder}/README.md",
        idea_text=(ROOT / "IDEA.md").read_text(encoding="utf-8"),
        tree=repotree.parse(block),
        breakdown_section=20 if folder == "v1" else 0,  # later versions are not in §20
        extra_roots=WORKSPACE_DIRS,
    )


def test_own_plans_pass_phase_lint() -> None:
    result = phaselint.lint(own_plan_set())
    assert len(result.phases) == 18
    assert [(i.code, i.rel, i.message) for i in result.issues] == []


def test_own_dependency_graph_matches_the_ledger() -> None:
    phases = {p.number: p.depends for p in phaselint.lint(own_plan_set()).phases}
    assert phases["00"] == [] and phases["13"] == ["11", "12"] and phases["12"] == ["08"]


def test_later_plan_versions_pass_phase_lint() -> None:
    for folder in sorted(
        p.name for p in (ROOT / "plans").iterdir() if p.is_dir() and p.name != "v1"
    ):
        result = phaselint.lint(own_plan_set(folder))
        assert result.phases, folder
        assert [(i.code, i.rel, i.message) for i in result.issues] == [], folder
