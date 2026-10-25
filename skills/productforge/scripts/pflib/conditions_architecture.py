"""ARCHITECTURE_LOCKED exit-gate conditions. Registered on import."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pflib import architecture, catalog, config, domain, records
from pflib.gates import ConditionResult, GateCondition, register
from pflib.index import WorkspaceIndex

STAGE = "ARCHITECTURE_LOCKED"
NO_DOC = ConditionResult(
    False, f"{catalog.ARCHITECTURE_PATH} does not exist yet (/productforge architect)"
)


def _sample(ids: list[str], limit: int = 8) -> str:
    return ", ".join(ids[:limit]) + (f" (+{len(ids) - limit} more)" if len(ids) > limit else "")


def _requirements(ws: Path) -> ConditionResult:
    if architecture.text_of(ws) is None:
        return NO_DOC
    cov = architecture.coverage(ws)
    if not cov.by_requirement:
        return ConditionResult(False, "no requirements to address")
    if cov.unaddressed:
        return ConditionResult(False, f"requirements not addressed: {_sample(cov.unaddressed)}")
    by_convention = sum(1 for v in cov.by_requirement.values() if v == ["convention"])
    return ConditionResult(True, f"all {len(cov.by_requirement)} requirements addressed "
                                 f"({by_convention} by convention)")  # fmt: skip


def _inferences(ws: Path) -> ConditionResult:
    if architecture.text_of(ws) is None:
        return NO_DOC
    cov = architecture.coverage(ws)
    bad = cov.unproposed + cov.multi_proposed
    if bad:
        return ConditionResult(False, f"inferences without exactly one proposal: {_sample(bad)}")
    n = len(domain.active(WorkspaceIndex(ws), "A"))
    return ConditionResult(True, f"all {n} inferences have a proposal")


def _invariants(ws: Path) -> ConditionResult:
    invs = domain.active(WorkspaceIndex(ws), "INV")
    bare = [i.id for i in invs if architecture.enforcement_kind(i.get("Enforced by")) is None]
    if not invs:
        return ConditionResult(False, "no invariants yet")
    if bare:
        return ConditionResult(False, f"invariants without a mechanism: {_sample(bare)}")
    return ConditionResult(True, f"{len(invs)} invariants, all enforced")


def _repo(ws: Path) -> ConditionResult:
    text = architecture.text_of(ws)
    if text is None:
        return NO_DOC
    paths, error = architecture.tree(text)
    if error:
        return ConditionResult(False, f"repository structure: {error}")
    return ConditionResult(True, f"repository structure declares {len(paths)} paths")


def _stack(ws: Path) -> ConditionResult:
    text = architecture.text_of(ws)
    if text is None:
        return NO_DOC
    rows = architecture.stack_rows(text)
    bad = [r[0] for r in rows if len(r) < 2 or architecture.INCOMPLETE_RE.match(r[1])]
    if not rows:
        return ConditionResult(False, "no stack table")
    if bad:
        return ConditionResult(False, f"stack choices still open: {', '.join(bad)}")
    return ConditionResult(True, f"stack fully named ({len(rows)} concerns)")


def _topics(ws: Path) -> ConditionResult:
    if architecture.text_of(ws) is None:
        return NO_DOC
    missing = architecture.coverage(ws).topics_missing
    if missing:
        return ConditionResult(False, f"mandatory topics not decided: {', '.join(missing)}")
    return ConditionResult(True, f"all {len(architecture.MANDATORY_TOPICS)} mandatory topics "
                                 "decided or explained")  # fmt: skip


def _is_open(value: str) -> bool:
    return bool(architecture.INCOMPLETE_RE.match(value))


def _external_services(ws: Path) -> ConditionResult:
    text = architecture.text_of(ws)
    if text is None:
        return NO_DOC
    rows = architecture.external_service_rows(text)
    if not rows:
        return ConditionResult(
            False, "## External services has no table (a product with none writes a row 'none')"
        )
    if len(rows) == 1 and rows[0][0].strip().lower() == "none":
        return ConditionResult(True, "no external services")
    not_applicable = {k.lower() for k in architecture.bullets(
        architecture.section(text, "Not applicable topics"))}  # fmt: skip
    index = WorkspaceIndex(ws)
    adrs = {a.id: a for _, a in index.records("ADR")}
    problems: list[str] = []
    for row in rows:
        cap = row[0] if row else ""
        if cap.strip().lower() in not_applicable:
            continue
        vendor = row[1] if len(row) > 1 else ""
        if _is_open(vendor) or vendor.strip().lower() in {"tbd", "none"}:
            problems.append(f"{cap}: vendor is not named")
            continue
        refs = records.parse_refs(row[2]) if len(row) > 2 else []
        if not refs:
            problems.append(f"{cap}: no ADR cited")
            continue
        for ref in refs:
            adr = adrs.get(ref)
            if adr is None or not records.is_active(adr):
                problems.append(f"{cap}: {ref} is missing or not active")
            elif adr.get("Topic").strip() != "vendor":
                problems.append(f"{cap}: {ref} does not have Topic: vendor")
    if problems:
        return ConditionResult(False, "; ".join(problems[:6]) + (" …" if len(problems) > 6 else ""))
    return ConditionResult(True, f"{len(rows)} external services, each with a vendor ADR")


def _toolchain(ws: Path) -> ConditionResult:
    text = architecture.text_of(ws)
    if text is None:
        return NO_DOC
    rows = architecture.toolchain_rows(text)
    if not rows:
        return ConditionResult(False, "no ## Toolchain table")
    by_concern = {r[0].strip().lower(): r for r in rows if r}
    concerns = [str(c) for c in config.resolve("architecture.toolchain_concerns", ws)]
    problems: list[str] = []
    for concern in concerns:
        row = by_concern.get(concern.strip().lower())
        if row is None:
            problems.append(f"{concern}: no row")
            continue
        version = row[2] if len(row) > 2 else ""
        verified = row[3] if len(row) > 3 else ""
        if _is_open(version) or architecture.UNPINNED_RE.match(version):
            problems.append(f"{concern}: version is not pinned")
        elif not architecture.VERIFIED_RE.match(verified.strip()):
            problems.append(f"{concern}: Verified must read 'YYYY-MM-DD <registry or URL>'")
    if problems:
        return ConditionResult(False, "; ".join(problems[:6]) + (" …" if len(problems) > 6 else ""))
    return ConditionResult(True, f"all {len(concerns)} concerns pinned and verified")


def _env_contract(ws: Path) -> ConditionResult:
    text = architecture.text_of(ws)
    if text is None:
        return NO_DOC
    rows = architecture.environment_rows(text)
    services = architecture.local_services(text)
    problems: list[str] = []
    if not rows:
        problems.append("## Environments has no variable rows")
    for row in rows:
        cells = (row + [""] * 4)[:4]
        open_cells = [i for i, c in enumerate(cells) if _is_open(c)]
        if open_cells:
            problems.append(f"{cells[0] or '(unnamed)'}: a cell is empty or TBD")
    if not services:
        problems.append("### Local services lists no service")
    for svc in services:
        _, _, value = svc.partition(":")
        if not value.strip() or _is_open(value) or not architecture.PORT_RE.search(value.strip()):
            problems.append(f"local service {svc.split(':')[0]!r} needs an image and a port")
    if problems:
        return ConditionResult(False, "; ".join(problems[:6]) + (" …" if len(problems) > 6 else ""))
    return ConditionResult(True, f"{len(rows)} variables, {len(services)} local services")


CONDITIONS: tuple[tuple[str, str, Callable[[Path], ConditionResult]], ...] = (
    ("G-AR-REQUIREMENTS-ADDRESSED", "every requirement is addressed by an ADR", _requirements),
    ("G-AR-INFERENCES-PROPOSED", "every inference has a proposed implementation", _inferences),
    ("G-AR-INVARIANTS", "invariants exist and are enforced", _invariants),
    ("G-AR-REPO-STRUCTURE", "repository structure is declared", _repo),
    ("G-AR-STACK-COMPLETE", "stack fully named", _stack),
    ("G-AR-MANDATORY-TOPICS", "mandatory ADR topics covered", _topics),
    ("G-AR-EXTERNAL-SERVICES", "every external service has a vendor ADR", _external_services),
    ("G-AR-TOOLCHAIN", "toolchain pinned and verified", _toolchain),
    ("G-AR-ENV-CONTRACT", "environment contract declared", _env_contract),
)

for _cid, _desc, _fn in CONDITIONS:
    register(STAGE, GateCondition(_cid, _desc, _fn))
