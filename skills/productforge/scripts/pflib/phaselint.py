"""Phase lint (IMPLEMENTATION_PLAN.md §16.4): is a phase plan executable by a fresh session?

``lint(PlanSet)`` checks phase files, the plans index and the implementation plan as plain text —
no workspace needed, so ProductForge's own ``plans/v1/`` is linted with the same rules
(``tests/e2e/test_dogfood_own_plans.py``). ``lint_root_docs`` checks the generated project
documents of a workspace.

Conventions the lint relies on (the phase-planner follows them; so do this repo's plans):

- the first line is ``# Phase NN — <Name>`` and the file is ``phase-NN-<slug>.md``;
- header lines ``**Status:**``, ``**Depends on:**`` (phase numbers or ``none``), ``**Goal:**``;
- the §16.2 ``##`` headings, in order (extra headings are allowed between them);
- tasks are a numbered list under ``## Tasks``, each naming a path in backticks;
- acceptance criteria are ``- [ ]`` / ``- [x]`` checkboxes;
- ``§N`` / ``§N.M`` cite the implementation plan; ``IDEA §N`` cites the vision document.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from pflib import catalog, ids, repotree

HEADINGS = (
    "Context",
    "Scope",
    "Tasks",
    "Data & schema changes",
    "API / contracts",
    "Acceptance criteria",
    "Test plan",
    "References",
    "Open questions / risks",
    "Definition of done",
)
TITLE_RE = re.compile(r"^# Phase (?P<n>\d{2}) — (?P<name>\S.*)$")
FILE_RE = re.compile(r"(?:^|/)phase-(?P<n>\d{2})-[a-z0-9-]+\.md$")
HEADER_RE = {
    key: re.compile(rf"^\*\*{re.escape(key)}:\*\*\s*(?P<v>.*)$", re.M)
    for key in ("Status", "Depends on", "Goal")
}
SECTION_RE = re.compile(r"^#{1,4}\s+(?P<n>\d+)\.(?P<m>\d+)?(?:\s|$)")
REF_RE = re.compile(r"§(?P<n>\d+)(?:\.(?P<m>\d+))?")
DOC_RE = re.compile(r"IDEA(?:\.md)?|IMPLEMENTATION_PLAN(?:\.md)?")
TICK_RE = re.compile(r"`([^`\n]+)`")
PATHLIKE_RE = re.compile(r"^[\w.@*{}<>/-]+$")
BARE_FILE_RE = re.compile(
    r"(?<![\w/.-])[\w-]+\.(?:md|py|json|ya?ml|toml|ts|tsx|js|jsx|sql|sh|css|html|txt|cfg|ini|lock)\b"
)
ROOT_FILES = ("Makefile", "Dockerfile", "LICENSE", "Procfile", "Justfile")
EXT_RE = re.compile(r"\.[A-Za-z][A-Za-z0-9]{0,5}$")
ID_LIST_RE = re.compile(r"^[A-Z]{1,3}(?:/[A-Z]{1,3})+$")  # "R/A", "W/D/F" — not paths
FENCE_RE = re.compile(r"^(```|~~~)")


@dataclass
class Issue:
    code: str
    rel: str
    message: str


@dataclass
class Phase:
    number: str
    name: str
    rel: str
    depends: list[str]
    depends_text: str
    sections: dict[str, str]
    order: list[str]
    text: str


@dataclass
class PlanSet:
    phases: dict[str, str]  # rel path → text
    plan_text: str | None = None  # IMPLEMENTATION_PLAN.md
    plan_rel: str = catalog.IMPLEMENTATION_PLAN_PATH
    readme_text: str | None = None  # the plans index
    readme_rel: str = catalog.PLANS_README_PATH
    idea_text: str | None = None  # the vision document, when phases cite "IDEA §N"
    tree: set[str] | None = None  # declared repository paths (repotree.parse)
    known_ids: set[str] | None = None  # record IDs that exist (workspace only)
    breakdown_section: int = 19  # the plan's "Phase breakdown" section number (0: not checked)
    max_tasks: int = 15
    min_acceptance: int = 3
    extra_roots: tuple[str, ...] = ()  # directories allowed besides the tree (e.g. workspace dirs)


@dataclass
class Result:
    issues: list[Issue] = field(default_factory=list)
    phases: list[Phase] = field(default_factory=list)

    def summary(self) -> list[dict[str, Any]]:
        return [
            {"number": p.number, "name": p.name, "file": p.rel, "depends_on": p.depends}
            for p in self.phases
        ]


# ----------------------------------------------------------------------------- parsing


def level2(text: str) -> tuple[list[str], dict[str, str]]:
    """``##`` headings in order and their bodies (fenced blocks are skipped)."""
    order: list[str] = []
    bodies: dict[str, list[str]] = {}
    current: str | None = None
    fenced = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            fenced = not fenced
        if not fenced and line.startswith("## "):
            current = line[3:].strip()
            order.append(current)
            bodies.setdefault(current, [])
            continue
        if current is not None:
            bodies[current].append(line)
    return order, {k: "\n".join(v) for k, v in bodies.items()}


def section_numbers(text: str) -> tuple[set[str], dict[str, set[str]]]:
    """Section numbers declared by headings, and numbered-list items directly under each §N."""
    heads: set[str] = set()
    items: dict[str, set[str]] = {}
    current: str | None = None
    fenced = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        m = SECTION_RE.match(line)
        if m:
            n, sub = m.group("n"), m.group("m")
            heads.add(f"{n}.{sub}" if sub else n)
            current = n if not sub else None
            continue
        if line.startswith("#"):
            current = None
            continue
        item = re.match(r"^(\d+)\.\s", line)
        if current is not None and item:
            items.setdefault(current, set()).add(item.group(1))
    return heads, items


def parse_phase(rel: str, text: str) -> tuple[Phase | None, list[Issue]]:
    issues: list[Issue] = []
    first = text.splitlines()[0] if text.strip() else ""
    title = TITLE_RE.match(first)
    file_n = FILE_RE.search(rel)
    if not title:
        issues.append(Issue("PHASE_HEADER_FIELDS", rel, "first line must be '# Phase NN — <Name>'"))
        return None, issues
    if file_n and file_n.group("n") != title.group("n"):
        issues.append(
            Issue(
                "PHASE_HEADER_FIELDS",
                rel,
                f"title says Phase {title.group('n')} but the file is phase-{file_n.group('n')}-…",
            )
        )
    values = {
        k: (m.group("v").strip() if (m := rx.search(text)) else None) for k, rx in HEADER_RE.items()
    }
    missing = [k for k, v in values.items() if not v]
    if missing:
        issues.append(
            Issue(
                "PHASE_HEADER_FIELDS",
                rel,
                f"missing header line(s): {', '.join(f'**{k}:**' for k in missing)}",
            )
        )
    deps_text = values["Depends on"] or ""
    depends = [] if deps_text.lower().startswith("none") else re.findall(r"\b\d{2}\b", deps_text)
    order, bodies = level2(text)
    return Phase(
        title.group("n"), title.group("name").strip(), rel, depends, deps_text, bodies, order, text
    ), issues


def cites_idea(line: str, pos: int) -> bool:
    """Does the § at ``pos`` cite the vision document? It belongs to the document named last
    before it ("IDEA §11, §33"), until the parenthesis that name was written in closes
    ("(… IDEA §18), status values (§6.3)" — §6.3 is the plan's)."""
    doc, doc_depth, depth = None, 0, 0
    for i, ch in enumerate(line[:pos]):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if doc is not None and depth < doc_depth:
                doc = None
        m = DOC_RE.match(line, i)
        if m and (i == 0 or not line[i - 1].isalnum()):
            doc, doc_depth = m.group(0), depth
    return doc is not None and doc.startswith("IDEA")


def path_tokens(line: str) -> list[str]:
    """Paths a task line names: backticked path-like tokens, plus bare file names (SKILL.md)."""
    out = []
    for raw in TICK_RE.findall(line):
        token = raw.strip()
        if " " in token:  # a command: its first word counts when it is a file (`pf.py deps …`)
            first = token.split(" ", 1)[0]
            if EXT_RE.search(first) and PATHLIKE_RE.match(first):
                out.append(first)
            continue
        if (
            token not in ROOT_FILES
            and not EXT_RE.search(token)
            and not token.endswith("/")
            and all(seg[:1].isupper() for seg in token.split("/"))
        ):
            continue  # "MVP/Decision/Score", "PHASE_HEADING_MISSING/ORDER": names, not paths
        if token in ROOT_FILES or (
            ("/" in token or EXT_RE.search(token))
            and PATHLIKE_RE.match(token)
            and not (ID_LIST_RE.match(token) or token.startswith(("http", "§")))
        ):
            out.append(token)
    bare = TICK_RE.sub(" ", line)
    out += [m.group(0) for m in BARE_FILE_RE.finditer(bare)]
    return out


def checkable(path: str) -> bool:
    """Patterns, absolute/URL paths and placeholder roots are not checked against the tree."""
    return not (path.startswith("/") or "*" in path or path.startswith("<"))


def _numbered(body: str) -> list[str]:
    return [ln for ln in body.splitlines() if re.match(r"^\d+\.\s", ln)]


def _in_tree(path: str, tree: set[str], extra_roots: tuple[str, ...]) -> bool:
    path = repotree.strip_dot(path)
    if "/" not in path.rstrip("/"):
        return True  # a bare file name, or a root file
    if repotree.contains(tree, path) or path.startswith(extra_roots):
        return True
    head = path.split("/", 1)[0] + "/"
    # relative to a declared directory: "pflib/merge.py" inside ".../scripts/pflib/"
    return any(d.endswith("/" + head) or d == head for d in tree if d.endswith("/"))


# ------------------------------------------------------------------------------- lint


def lint(ps: PlanSet) -> Result:
    res = Result()
    for rel, text in sorted(ps.phases.items()):
        phase, issues = parse_phase(rel, text)
        res.issues.extend(issues)
        if phase is not None:
            res.phases.append(phase)
    res.phases.sort(key=lambda p: p.number)
    numbers = {p.number for p in res.phases}
    plan_heads, plan_items = section_numbers(ps.plan_text) if ps.plan_text else (set(), {})
    idea_heads, idea_items = section_numbers(ps.idea_text) if ps.idea_text else (set(), {})

    cycles, cycle_edges = _cycles(res.phases)
    for p in res.phases:
        add = res.issues.append
        # headings
        present = [h for h in p.order if h in HEADINGS]
        missing = [h for h in HEADINGS if h not in p.sections]
        if missing:
            add(Issue("PHASE_HEADING_MISSING", p.rel, f"missing ## {', ## '.join(missing)}"))
        expected = [h for h in HEADINGS if h in present]
        if present != expected:
            add(
                Issue(
                    "PHASE_HEADING_ORDER",
                    p.rel,
                    "headings out of order; expected " + " → ".join(expected),
                )
            )
        # dependencies
        if p.number == "00" and p.depends_text and not p.depends_text.lower().startswith("none"):
            add(Issue("PHASE00_HAS_DEPS", p.rel, "phase 00 must depend on none"))
        for d in p.depends:
            if d not in numbers:
                add(
                    Issue("PHASE_DEP_UNKNOWN", p.rel, f"depends on phase {d}, which does not exist")
                )
            elif d >= p.number and (p.number, d) not in cycle_edges:  # cycles: reported once
                add(Issue("PHASE_DEP_FORWARD", p.rel, f"depends on later phase {d}"))
        # section references
        for line in p.text.splitlines():
            for m in REF_RE.finditer(line):
                idea = cites_idea(line, m.start())
                n, sub = m.group("n"), m.group("m")
                heads, items, label = (
                    (idea_heads, idea_items, "IDEA")
                    if idea
                    else (plan_heads, plan_items, "the plan")
                )
                if (ps.idea_text if idea else ps.plan_text) is None:
                    continue
                ok = (f"{n}.{sub}" in heads or sub in items.get(n, set())) if sub else n in heads
                if not ok:
                    ref = f"§{n}" + (f".{sub}" if sub else "")
                    msg = f"{ref} does not exist in {label}"
                    add(Issue("PHASE_SECTION_REF_DANGLING", p.rel, msg))
        # tasks
        tasks = _numbered(p.sections.get("Tasks", ""))
        if len(tasks) > ps.max_tasks:
            add(
                Issue(
                    "PHASE_TOO_MANY_TASKS",
                    p.rel,
                    f"{len(tasks)} tasks (at most {ps.max_tasks}, phases.max_tasks): split it",
                )
            )
        for line in tasks:
            paths = path_tokens(line)
            if not paths:
                add(
                    Issue(
                        "PHASE_TASK_NO_PATH",
                        p.rel,
                        f"task names no path in backticks: {line[:70]!r}",
                    )
                )
            elif ps.tree is not None:
                outside = [
                    x for x in paths if checkable(x) and not _in_tree(x, ps.tree, ps.extra_roots)
                ]
                if outside:
                    add(
                        Issue(
                            "PHASE_PATH_OUTSIDE_TREE",
                            p.rel,
                            f"paths outside the repository structure: {', '.join(outside)}",
                        )
                    )
        # acceptance
        boxes = re.findall(r"^- \[[ xX]\]", p.sections.get("Acceptance criteria", ""), re.M)
        if len(boxes) < ps.min_acceptance:
            add(
                Issue(
                    "PHASE_TOO_FEW_ACCEPTANCE",
                    p.rel,
                    f"{len(boxes)} acceptance criteria (need ≥ {ps.min_acceptance})",
                )
            )
        # record references
        if ps.known_ids is not None:
            refs = {
                r
                for r in ids.ANY_ID_RE.findall(p.sections.get("References", ""))
                if ids.parse(r, strict=False) is not None
            }
            dangling = sorted(refs - ps.known_ids)
            if dangling:
                add(
                    Issue(
                        "PHASE_ID_REF_DANGLING",
                        p.rel,
                        f"## References cites missing records: {', '.join(dangling)}",
                    )
                )
    res.issues.extend(cycles)
    res.issues.extend(_index(ps, res.phases))
    return res


def _cycles(phases: list[Phase]) -> tuple[list[Issue], set[tuple[str, str]]]:
    """Cycle findings, and the (phase, dependency) edges that lie on a cycle."""
    graph = {p.number: list(p.depends) for p in phases}
    rels = {p.number: p.rel for p in phases}
    out: list[Issue] = []
    edges: set[tuple[str, str]] = set()
    state: dict[str, int] = {}

    def visit(n: str, path: list[str]) -> None:
        state[n] = 1
        for d in graph.get(n, []):
            if state.get(d) == 1:
                cycle = [*path[path.index(d) :], d]
                edges.update(zip(cycle, cycle[1:], strict=False))
                out.append(
                    Issue("PHASE_DEP_CYCLE", rels[n], "dependency cycle: " + " → ".join(cycle))
                )
            elif d in graph and not state.get(d):
                visit(d, [*path, d])
        state[n] = 2

    for n in sorted(graph):
        if not state.get(n):
            visit(n, [n])
    return out, edges


def _index(ps: PlanSet, phases: list[Phase]) -> list[Issue]:
    out: list[Issue] = []
    files = {p.number: p.rel.rsplit("/", 1)[-1] for p in phases}
    if ps.readme_text is not None:
        rows = re.findall(
            r"^\|\s*(\d{2})\s*\|.*?\(([^)]*phase-\d{2}-[^)]+\.md)\)", ps.readme_text, re.M
        )
        listed = {n: f.rsplit("/", 1)[-1] for n, f in rows}
        if set(listed) != set(files):
            gone, extra = sorted(set(files) - set(listed)), sorted(set(listed) - set(files))
            out.append(
                Issue(
                    "PHASE_INDEX_MISMATCH",
                    ps.readme_rel,
                    f"index vs files — not listed: {', '.join(gone) or '–'}; "
                    f"no file: {', '.join(extra) or '–'}",
                )
            )
        for n, name in sorted(listed.items()):
            if n in files and files[n] != name:
                out.append(
                    Issue(
                        "PHASE_INDEX_MISMATCH",
                        ps.readme_rel,
                        f"phase {n} links {name} but the file is {files[n]}",
                    )
                )
    if ps.plan_text is not None and ps.breakdown_section:
        body = ""
        for line_no, line in enumerate(ps.plan_text.splitlines()):
            if re.match(rf"^##\s+{ps.breakdown_section}\.\s", line):
                rest = ps.plan_text.splitlines()[line_no + 1 :]
                body = "\n".join(
                    next(
                        iter([rest[:i] for i, ln in enumerate(rest) if re.match(r"^##\s", ln)]),
                        rest,
                    )
                )
                break
        planned = set(re.findall(r"^\|\s*(\d{2})\s*\|", body, re.M))
        if planned != set(files):
            out.append(
                Issue(
                    "PHASE_INDEX_MISMATCH",
                    ps.plan_rel,
                    f"§{ps.breakdown_section} lists {', '.join(sorted(planned)) or 'nothing'}"
                    f" but the phase files are {', '.join(sorted(files)) or 'none'}",
                )
            )
    return out


# --------------------------------------------------------------------------- root docs

PLAN_SECTIONS = (
    "Product overview",
    "V1 scope",
    "Architecture",
    "Technology stack",
    "Repository structure",
    "Data model",
    "Authentication",
    "Authorization",
    "Major subsystems",
    "Integrations",
    "Async processing",
    "Realtime behaviour",
    "Search",
    "Security",
    "Observability",
    "Infrastructure",
    "Deployment",
    "Cross-cutting invariants",
    "Phase breakdown",
    "Testing strategy",
    "Glossary",
)
_README, _PLAN, _CLAUDE, _DEVELOPMENT, _STARTUP = catalog.ROOT_DOCS
ROOT_HEADINGS: dict[str, tuple[str, ...]] = {
    _README: ("What this is", "Status", "Documents", "How this was produced"),
    _CLAUDE: (
        "Golden rules",
        "Stack",
        "Layout",
        "Commands",
        "Conventions",
        "Security",
        "Extension recipes",
        "Anti-patterns",
        "Testing expectations",
        "Executing a phase",
    ),
    _DEVELOPMENT: (
        "Prerequisites",
        "Setup",
        "Running locally",
        "Testing",
        "Linting",
        "Database",
        "Environment variables",
        "Troubleshooting",
    ),
    _STARTUP: ("Step 0 — Read", "Step 1 — Wait", "Execution protocol"),
}


def lint_root_docs(texts: dict[str, str | None], invariant_count: int) -> list[Issue]:
    """Required sections of the generated project documents (IMPLEMENTATION_PLAN §16.1)."""
    out: list[Issue] = []
    plan = texts.get(_PLAN)
    if plan is None:
        out.append(Issue("ROOTDOC_SECTION_MISSING", _PLAN, "file is missing"))
    else:
        found = {
            int(m.group(1)): m.group(2).strip()
            for m in re.finditer(r"^## (\d+)\. (.+)$", plan, re.M)
        }
        bad = [
            f"{i}. {name}" for i, name in enumerate(PLAN_SECTIONS, start=1) if found.get(i) != name
        ]
        if bad:
            out.append(
                Issue(
                    "ROOTDOC_SECTION_MISSING",
                    _PLAN,
                    f"sections missing or renamed: {', '.join(bad[:6])}"
                    + (" …" if len(bad) > 6 else ""),
                )
            )
    for rel, needed in ROOT_HEADINGS.items():
        text = texts.get(rel)
        if text is None:
            out.append(Issue("ROOTDOC_SECTION_MISSING", rel, "file is missing"))
            continue
        order, bodies = level2(text)
        missing = [h for h in needed if h not in bodies]
        if missing:
            out.append(Issue("ROOTDOC_SECTION_MISSING", rel, f"missing ## {', ## '.join(missing)}"))
    claude = texts.get(_CLAUDE)
    if claude is not None:
        rules = _numbered(level2(claude)[1].get("Golden rules", ""))
        if len(rules) != invariant_count:
            out.append(
                Issue(
                    "ROOTDOC_SECTION_MISSING",
                    _CLAUDE,
                    f"## Golden rules has {len(rules)} rules but there are "
                    f"{invariant_count} invariants (one rule per INV)",
                )
            )
    return out
