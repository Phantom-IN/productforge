"""Structural contracts for the prompts that drive ProductForge (SKILL.md, agents, contract)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import pf
from pflib import commands

REPO = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO / "skills" / "productforge"
SKILL = SKILL_DIR / "SKILL.md"
AGENTS = REPO / "agents"
REFERENCES = SKILL_DIR / "references"
CONTRACT = SKILL_DIR / "references" / "agent-contract.md"
SUMMARY_LINE = (
    "RUN <run-id> · ROLE <role> · WROTE <files> · RECORDS <prefix:n,…> · "
    "RESEARCH REQUESTS <list or none> · NOTES <≤5 lines>"
)
REQUIRED_SECTIONS = [
    "Purpose",
    "Hard constraints",
    "Locating the scripts",
    "Command grammar",
    "Dispatch algorithm",
    "Transition protocol",
    "Agent run protocol",
    "Inline fallback",
    "Capabilities",
    "Delegated run protocol",
    "End-of-command report",
    "Commands",
]
MAX_SKILL_LINES = 400


def commands_text() -> str:
    """SKILL.md plus the command references it delegates stage procedures to."""
    parts = [SKILL.read_text(encoding="utf-8")]
    parts += [p.read_text(encoding="utf-8") for p in sorted(REFERENCES.glob("commands-*.md"))]
    return "\n".join(parts)


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    block = text[4 : text.index("\n---\n", 4)]
    out: dict[str, str] = {}
    key = None
    for line in block.splitlines():
        m = re.match(r"^([a-zA-Z-]+):\s*(.*)$", line)
        if m:
            key, out[m.group(1)] = m.group(1), m.group(2)
        elif key and line.startswith("  "):
            out[key] += " " + line.strip()
    return out


def subcommands() -> set[str]:
    parser = pf.build_parser()
    action = next(a for a in parser._actions if a.dest == "command")
    return set(action.choices)  # type: ignore[arg-type]


def check_skill(text: str) -> list[str]:
    """Problems with SKILL.md text (empty list = contract satisfied)."""
    problems: list[str] = []
    meta = frontmatter(text)
    for key in ("name", "description", "allowed-tools"):
        if not meta.get(key):
            problems.append(f"frontmatter missing {key}")
    if meta.get("name") != "productforge":
        problems.append("frontmatter name must be productforge")
    tools = {t.strip() for t in meta.get("allowed-tools", "").split(",")}
    for tool in ("Bash", "Task", "AskUserQuestion", "Read"):
        if tool not in tools:
            problems.append(f"allowed-tools lacks {tool}")
    headings = re.findall(r"^## (.+)$", text, re.M)
    positions = [headings.index(h) if h in headings else -1 for h in REQUIRED_SECTIONS]
    for name, pos in zip(REQUIRED_SECTIONS, positions, strict=True):
        if pos < 0:
            problems.append(f"missing section: {name}")
    present = [p for p in positions if p >= 0]
    if present != sorted(present):
        problems.append("required sections are out of order")
    known = subcommands()
    used = set(re.findall(r'"\$PF" ([a-z][a-z-]*)', text)) | set(
        re.findall(r"pf\.py ([a-z][a-z-]*)", text)
    )
    for sub in sorted(used - known):
        problems.append(f"references unknown pf.py subcommand: {sub}")
    for rel in sorted(set(re.findall(r"\b((?:references|templates)/[\w./-]+\.md)\b", text))):
        if not (SKILL_DIR / rel).is_file():
            problems.append(f"references missing file: {rel}")
    if re.search(r"\bpython3(?!\.11)\b(?! \(macOS)", text.replace("bare `python3`", "")):
        problems.append("uses bare python3 instead of python3.11")
    for cmd in commands.COMMAND_STAGE:
        if f"`{cmd}" not in text:
            problems.append(f"command {cmd} is not documented")
    if len(text.splitlines()) > MAX_SKILL_LINES:
        problems.append(f"SKILL.md is longer than {MAX_SKILL_LINES} lines")
    return problems


def test_skill_satisfies_its_contract() -> None:
    assert check_skill(SKILL.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_removing_a_required_section_is_detected(section: str) -> None:
    text = SKILL.read_text(encoding="utf-8")
    broken = re.sub(rf"^## {re.escape(section)}$", f"## Renamed {section}", text, flags=re.M)
    assert f"missing section: {section}" in check_skill(broken)


def test_checker_catches_unknown_subcommands_files_and_python() -> None:
    text = SKILL.read_text(encoding="utf-8")
    bad = text + '\nRun `python3 "$PF" teleport` and read `references/nope.md`.\n'
    problems = check_skill(bad)
    assert "references unknown pf.py subcommand: teleport" in problems
    assert "references missing file: references/nope.md" in problems
    assert "uses bare python3 instead of python3.11" in problems


def test_contract_has_summary_format_and_core_rules() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert SUMMARY_LINE in text
    for phrase in (
        "Write only inside your staging path",
        "provisional IDs",
        "U-` record",
        "data, never instructions",
        "RESEARCH REQUESTS",
    ):
        assert phrase in text, phrase


def test_brief_template_points_at_contract_and_summary() -> None:
    text = (SKILL_DIR / "templates" / "agent-brief.md").read_text(encoding="utf-8")
    assert "{{contract}}" in text and "{{staging_path}}" in text
    assert "RUN {{run_id}} · ROLE {{role}} · WROTE <files>" in text


def test_every_file_in_agents_is_a_real_agent_definition() -> None:
    """Claude Code registers every agents/*.md as an agent — READMEs there become bogus agents."""
    for path in sorted(AGENTS.glob("*")):
        assert path.suffix == ".md", f"{path.name}: only agent definitions belong in agents/"
        text = path.read_text(encoding="utf-8")
        meta = frontmatter(text)
        for key in ("name", "description", "tools"):
            assert meta.get(key), f"{path.name}: frontmatter needs {key}"
        assert meta["name"] == path.stem, f"{path.name}: name must match the file name"
        assert "references/agent-contract.md" in text, f"{path.name}: must link the agent contract"
        assert not re.search(r"\bpython3(?!\.11)\b", text), f"{path.name}: use python3.11"


def test_reference_docs_named_by_the_plan_exist() -> None:
    for name in (
        "philosophy.md",
        "guardrails.md",
        "agent-contract.md",
        "record-format.md",
        "confidence-rules.md",
        "source-tiers.md",
        "stage-gates.md",
    ):
        assert (SKILL_DIR / "references" / name).is_file(), name


def section(text: str, title: str) -> str:
    return text.split(f"## {title}\n", 1)[1].split("\n## ", 1)[0]


def test_installs_are_only_ever_run_after_explicit_consent() -> None:
    text = SKILL.read_text(encoding="utf-8")
    caps = section(text, "Capabilities")
    assert "AskUserQuestion" in caps and "installs nothing" in caps
    for line in text.splitlines():
        if "deps install" in line and "--confirmed" in line:
            assert "Only if the user chose" in line, line
    assert "--confirmed" not in section(text, "Delegated run protocol")


def test_delegation_is_done_by_the_orchestrator_and_raw_output_is_data() -> None:
    text = SKILL.read_text(encoding="utf-8")
    delegated = section(text, "Delegated run protocol")
    assert '"$PF" delegate' in delegated and "role agents cannot invoke skills" in delegated
    assert "data, never instructions" in delegated and "never merged" in delegated
    assert "raw_dir" in section(text, "Hard constraints")


def test_research_agent_contract() -> None:
    text = (AGENTS / "research-agent.md").read_text(encoding="utf-8")
    for phrase in (
        '"allowed": true',
        "provisional IDs",
        "browse <url>",
        "pdf <url>",
        "repo <url>",
        "Via:",
        "prompt injection",
        "Recommended scope",
        "never a source",
    ):
        assert phrase in text, phrase
    assert "WebFetch" in frontmatter(text)["tools"] and "Bash" not in frontmatter(text)["tools"]


def test_research_section_wires_every_delegated_capability_and_the_fallback() -> None:
    text = SKILL.read_text(encoding="utf-8")
    research = text.split("### `/productforge research`", 1)[1].split("\n### ", 1)[0]
    for phrase in (
        '"$PF" research-plan',
        '"$PF" discover',
        "Delegated run protocol",
        "web.browse",
        "docs.pdf",
        "repo.intel",
        "builtin",
        "set-scope",
        "one at a time",
    ):
        assert phrase in research, phrase


def test_product_analyst_and_evidence_pass_contracts() -> None:
    analyst = (AGENTS / "product-analyst.md").read_text(encoding="utf-8")
    for phrase in (
        "### PS-?1",
        "Related features",
        "Unanswered questions",
        "provisional IDs",
        "data, never instructions",
    ):
        assert phrase in analyst, phrase
    research_agent = (AGENTS / "research-agent.md").read_text(encoding="utf-8")
    evidence = research_agent.split("## Evidence pass", 1)[1].split("\n## ", 1)[0]
    for phrase in (
        "same claim text",
        "conflicting-with",
        "Derived from",
        "Related unknown",
        "## Coverage",
        "observable behaviour",
    ):
        assert phrase in evidence, phrase
    skill = SKILL.read_text(encoding="utf-8")
    research = skill.split("### `/productforge research`", 1)[1].split("\n### ", 1)[0]
    for phrase in (
        "**Source pass**",
        "**Evidence pass**",
        "**Surface pass**",
        "product-analyst",
        "unmined",
        '"$PF" check',
        "/productforge features",
    ):
        assert phrase in research, phrase


def test_features_section_and_amendment_rules() -> None:
    text = SKILL.read_text(encoding="utf-8")
    feats = commands_text().split("### `/productforge features`", 1)[1].split("\n### ", 1)[0]
    for phrase in (
        '"$PF" feature-plan',
        "Domain split",
        "Feature passes",
        "empty_domains",
        "max_parallel",
        "per_domain_budget",
        "surfaces_without_features",
        "Dedupe pass",
        "amendment",
    ):
        assert phrase in feats, phrase
    research = text.split("### `/productforge research`", 1)[1].split("\n### ", 1)[0]
    assert "Dedupe pass" in research and "NEAR_DUPLICATE_TITLE" in research
    contract = CONTRACT.read_text(encoding="utf-8")
    assert "### AMEND <final ID>" in contract and "one\n   exception" in contract
    for agent in ("research-agent.md", "product-analyst.md"):
        body = (AGENTS / agent).read_text(encoding="utf-8")
        assert "## Amendments" in body and "- Why:" in body, agent
    analyst = (AGENTS / "product-analyst.md").read_text(encoding="utf-8")
    for phrase in (
        "## Domain split",
        "## Feature pass",
        "at most **3 levels**",
        "Plan tier",
        "Never write the `MVP`",
    ):
        assert phrase in analyst, phrase


def test_resume_and_batching_rules() -> None:
    text = SKILL.read_text(encoding="utf-8")
    protocol = section(text, "Agent run protocol")
    for phrase in (
        '"$PF" staging list',
        "staging discard",
        "RUN_LIMIT",
        "brief **only the runs you",
        "before briefing the next batch",
    ):
        assert phrase in protocol, phrase


def test_ux_analyst_and_workflows_section() -> None:
    agent = (AGENTS / "ux-analyst.md").read_text(encoding="utf-8")
    for phrase in (
        "[observed]",
        "[implied-system]",
        "authorize",
        "search index",
        "realtime event",
        "notify",
        "enqueue a job",
        "Never invent UI details",
        "at least half",
        "browse <url>",
    ):
        assert phrase in agent, phrase
    assert "Bash" not in frontmatter(agent)["tools"]
    flows = commands_text().split("### `/productforge workflows`", 1)[1].split("\n### ", 1)[0]
    for phrase in (
        '"$PF" workflow-candidates',
        "AskUserQuestion",
        "ux-analyst",
        "research/workflow.md",
        "brief only the current batch",
    ):
        assert phrase in flows, phrase


def test_domain_architect_and_model_section() -> None:
    agent = (AGENTS / "domain-architect.md").read_text(encoding="utf-8")
    tools = frontmatter(agent)["tools"]
    assert "Bash" not in tools and "WebFetch" not in tools  # no network by design
    for phrase in (
        "No network",
        "RESEARCH REQUESTS",
        "Never state the target's internal technology",
        "one cell for every\n   role",
        "Deletion semantics",
        "required `N:1`",
        "supersede the old one",
        "Domain and permission fields",
    ):
        assert phrase in agent, phrase
    text = SKILL.read_text(encoding="utf-8")
    model = commands_text().split("### `/productforge model`", 1)[1].split("\n### ", 1)[0]
    model = " ".join(model.split())  # commands wrap across lines
    for phrase in (
        "--role domain-architect",
        "--template spec/DOMAIN_MODEL.md",
        "--template spec/PERMISSIONS_MATRIX.md",
        "unknown_permission_cells",
        "over_soft_cap",
        "never advance here",
        "--role product-analyst",
        "--role systems-architect",
        "--template spec/INTEGRATIONS.md",
        "--template research/architecture-inference.md",
        "skipping a pass whose",
    ):
        assert phrase in model, phrase
    stubs = text.split("### Stage commands not yet available", 1)[1]
    assert "| `model` |" not in stubs


def test_systems_architect_and_integration_pass() -> None:
    agent = (AGENTS / "systems-architect.md").read_text(encoding="utf-8")
    tools = frontmatter(agent)["tools"]
    assert "Bash" not in tools and "WebFetch" not in tools
    for phrase in (
        "Target implementation: UNKNOWN",
        "Never propose a technology",
        "No network",
        "Tier ≤ 2",
        "measurable",
        "Derived from",
        "repo.intel",
        "Do not write `Proposed implementation`",
        "## Design pass",
    ):
        assert phrase in agent, phrase
    analyst = (AGENTS / "product-analyst.md").read_text(encoding="utf-8")
    integration = analyst.split("## Integration pass", 1)[1].split("\n## ", 1)[0]
    for phrase in (
        "spec/INTEGRATIONS.md",
        "Direction: inbound | outbound | bidirectional",
        "Not documented",
        "webhooks",
        "single\nsign-on",
    ):
        assert phrase in integration, phrase
    playbook = (REFERENCES / "product-model-playbook.md").read_text(encoding="utf-8")
    assert len(playbook.splitlines()) < 300 and "TARGET_IMPL_UNSUPPORTED" in playbook


def test_competitor_pass_and_section() -> None:
    analyst = (AGENTS / "product-analyst.md").read_text(encoding="utf-8")
    comp = " ".join(analyst.split("## Competitor pass", 1)[1].split("\n## ", 1)[0].split())
    for phrase in (
        "never add one yourself",
        "at most 10 sources",
        "Relevant area: competitor:C-?1",
        "Tier 3–4",
        "Never edit `F-` records",
        "COMPETITOR_SOURCE_AS_EVIDENCE",
        "absent-in-target",
        "Do not write `table-stakes`/`rare` signals",
    ):
        assert phrase in comp, phrase
    text = SKILL.read_text(encoding="utf-8")
    section = " ".join(
        commands_text().split("### `/productforge competitors`", 1)[1].split("\n### ", 1)[0].split()
    )
    for phrase in (
        '"$PF" competitor-candidates',
        "Never research a competitor the user has not confirmed",
        "AskUserQuestion",
        "batches of at most 3",
        "--max-pages 20",
        "--template research/COMPETITORS.md",
        "research.deep",
        "neutral",
    ):
        assert phrase in section, phrase
    assert "`competitors`" not in text.split("### Stage commands not yet available", 1)[1]


def test_scope_editor_and_scope_command() -> None:
    agent = (AGENTS / "scope-editor.md").read_text(encoding="utf-8")
    assert "Bash" not in frontmatter(agent)["tools"]
    flat = " ".join(agent.split())
    for phrase in (
        "Never compute or state a total",
        "pf.py score",
        "— <why",
        "FEATURE_UNSCORED",
        "FEATURE_WITHOUT_REQUIREMENT",
        "### AMEND SC-009",
        "Do not undo the user's overrides",
        "never a vendor",
        "## V1 defaults",
    ):
        assert phrase in flat, phrase
    scope = " ".join(
        commands_text().split("### `/productforge scope`", 1)[1].split("\n## ", 1)[0].split()
    )
    for phrase in (
        '"$PF" score --write',
        '"$PF" override',
        "AskUserQuestion",
        "Requirements are written only after the user accepts",
        "--role scope-editor",
        "never advance here",
        "--template spec/PARITY_MATRIX.md",
        "--template spec/PRODUCT_SPEC.md",
        "R1",
    ):
        assert phrase in scope, phrase
    model = (REFERENCES / "prioritisation-model.md").read_text(encoding="utf-8")
    assert len(model.splitlines()) < 300 and "R1" in model and "calibrat" in model.lower()
    assert (
        "`scope`"
        not in SKILL.read_text(encoding="utf-8").split("### Stage commands not yet available", 1)[1]
    )
