"""Agent briefs — ``pf.py brief`` (IMPLEMENTATION_PLAN.md §9.1).

The orchestrator never improvises a brief: it renders ``templates/agent-brief.md`` with
workspace values so every agent run gets the same contract, staging path and scope. With an
existing ``run_id`` the brief becomes a **repair brief**: the run is preflighted (merged into
a scratch copy and validated) and the findings are listed, translated back to the agent's
provisional IDs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pflib import config, ids, merge, state, workspace
from pflib.errors import CheckFailed, UsageError
from pflib.scaffold import TEMPLATES_DIR

SKILL_DIR = TEMPLATES_DIR.parent
BRIEF_TEMPLATE = TEMPLATES_DIR / "agent-brief.md"
CONTRACT = SKILL_DIR / "references" / "agent-contract.md"
PLACEHOLDER_RE = re.compile(r"\{\{([a-z_]+)\}\}")


@dataclass
class Brief:
    run_id: str
    staging_path: Path
    repair: bool
    findings: int
    text: str
    max_repair_loops: int = 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "staging_path": str(self.staging_path),
            "repair": self.repair,
            "findings": self.findings,
            "max_repair_loops": self.max_repair_loops,
            "brief": self.text,
        }


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "none"


def _staged_files(run_dir: Path) -> list[Path]:
    return [
        p
        for p in run_dir.rglob("*.md")
        if not any(part.startswith(".") for part in p.relative_to(run_dir).parts)
        and p.relative_to(run_dir).parts[0] != workspace.RAW
    ]


def _repair_findings(ws: Path, run_id: str) -> tuple[int, str]:
    result = merge.preflight(ws, run_id)
    if result["merge_error"]:
        err = result["merge_error"]
        return 1, f"- {err['error']}: {err['message']}"
    report = result["report"] or {}
    id_map: dict[str, str] = report.get("id_map", {})
    finals = list(id_map.values())
    allocated = set(report.get("new_ids", []))
    # Show findings in the agent's own provisional IDs for records this run creates (1:1).
    new_ids = {
        final: prov
        for prov, final in id_map.items()
        if final in allocated and finals.count(final) == 1
    }

    def back(text: str) -> str:
        return ids.ANY_ID_RE.sub(lambda m: new_ids.get(m.group(0), m.group(0)), text)

    lines = [
        f"- {f['severity'].upper()} {f['code']} {back(f['record_id'] or f['artifact'] or '')}: "
        f"{back(f['message'])}"
        for f in result["findings"]
    ]
    return result["errors"] + result["warnings"], "\n".join(lines) if lines else "none"


def _check_pending(ws: Path) -> None:
    limit = int(config.resolve("agents.max_pending_runs", ws))
    pending = workspace.pending_runs(ws)
    if len(pending) >= limit:
        ids_ = ", ".join(p["run_id"] for p in pending)
        raise UsageError(
            f"{len(pending)} staging runs are still unmerged (limit agents.max_pending_runs="
            f"{limit}): {ids_}. Preflight and merge them (or `pf.py staging discard`) first.",
            code="RUN_LIMIT",
            details={"pending": [p["run_id"] for p in pending]},
        )


def _check_observe_input(rel: str) -> None:
    """Agents read a session's ``summary.json``, never its raw files (§23.1)."""
    parts = Path(rel).as_posix().strip("/").split("/")
    if parts[:2] == [workspace.PF_DIR, workspace.OBSERVE] and parts[-1] != "summary.json":
        raise UsageError(
            f"{rel}: briefs list an observe session's summary.json, never its raw files "
            "(events, HAR, screens); run `pf.py observe ingest <session>` first",
            code="BRIEF_RAW_SESSION",
        )


def render(
    ws: Path,
    role: str,
    task: str,
    partition: str | None = None,
    inputs: list[str] | None = None,
    templates: list[str] | None = None,
    budget: str | None = None,
    run_id: str | None = None,
) -> Brief:
    if not task.strip():
        raise UsageError("brief needs a non-empty --task", code="BAD_BRIEF")
    st = state.load(ws)
    repair = False
    findings, findings_text = 0, "none"
    raw_files: list[str] = []
    if run_id:
        run_dir = workspace.staging_dir(ws, run_id)
        if not run_dir.is_dir():
            raise UsageError(f"no staging run {run_id!r}", code="NO_SUCH_RUN")
        if _staged_files(run_dir):
            repair = True
            findings, findings_text = _repair_findings(ws, run_id)
        raw = run_dir / workspace.RAW
        raw_files = sorted(str(p) for p in raw.rglob("*") if p.is_file()) if raw.is_dir() else []
    else:
        _check_pending(ws)
        run_id, run_dir = workspace.create_staging_run(ws, role)

    for rel in inputs or []:
        _check_observe_input(rel)
    input_lines = [
        str(ws / rel) + ("" if (ws / rel).exists() else " (does not exist yet)")
        for rel in inputs or []
    ]
    template_lines = []
    for name in templates or []:
        path = TEMPLATES_DIR / name
        if not path.is_file():
            raise UsageError(
                f"unknown template {name!r} (under {TEMPLATES_DIR})", code="BAD_TEMPLATE"
            )
        template_lines.append(str(path))
    scope = st.scope.get("text") or "not set"
    if st.scope.get("text") and not st.scope.get("accepted"):
        scope += " (not yet accepted)"
    values = {
        "role": role,
        "run_id": run_id,
        "staging_path": str(run_dir),
        "workspace": str(ws),
        "product_name": st.product["name"],
        "target_url": st.product["target_url"],
        "open_stage": st.state.value,
        "scope": scope,
        "task": task.strip(),
        "partition": partition or "none — the whole task",
        "inputs": _bullets(input_lines),
        "templates": _bullets(template_lines),
        "budget": budget or "no explicit budget; stay within the task",
        "validator_findings": findings_text,
        "raw_material": _bullets(raw_files),
        "contract": str(CONTRACT),
    }
    text = BRIEF_TEMPLATE.read_text(encoding="utf-8")
    text = PLACEHOLDER_RE.sub(lambda m: values.get(m.group(1), m.group(0)), text)
    leftover = sorted(set(PLACEHOLDER_RE.findall(text)))
    if leftover:
        raise CheckFailed(f"agent-brief.md has unknown placeholders: {leftover}", code="BAD_BRIEF")
    loops = int(config.resolve("agents.max_repair_loops", ws))
    return Brief(run_id, run_dir, repair, findings, text, loops)


BRIEF_BLOCK_RE = re.compile(r"^```brief\n(.*?)^```$", re.S | re.M)


@dataclass
class Delegation:
    run_id: str
    raw_dir: Path
    capability: str
    provider: str
    kind: str
    invoke: str | None
    prompt: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "raw_dir": str(self.raw_dir),
            "capability": self.capability,
            "provider": self.provider,
            "kind": self.kind,
            "invoke": self.invoke,
            "prompt": self.prompt,
        }


def render_delegation(
    ws: Path,
    provider_id: str,
    questions: str,
    allowed_urls: list[str] | None = None,
    run_id: str | None = None,
) -> Delegation:
    """Prompt for a delegated provider (§9.4), rendered from its adapter's ```brief block.

    Creates (or reuses) a staging run whose ``raw/`` folder receives the provider's output; the
    normalising role agent then works in the same run.
    """
    from pflib import capabilities

    if not questions.strip():
        raise UsageError("delegate needs a non-empty --task", code="BAD_BRIEF")
    reg = capabilities.load_registry()
    prov = reg.provider(provider_id)
    cap_id = next(c.id for c in reg.capabilities.values() if c.provider(provider_id) is prov)
    assert prov.adapter is not None
    adapter_text = (capabilities.ADAPTERS_DIR / prov.adapter).read_text(encoding="utf-8")
    block = BRIEF_BLOCK_RE.search(adapter_text)
    if block is None:
        raise CheckFailed(f"adapter {prov.adapter} has no ```brief block", code="BAD_ADAPTER")
    st = state.load(ws)
    if run_id:
        run_dir = workspace.staging_dir(ws, run_id)
        if not run_dir.is_dir():
            raise UsageError(f"no staging run {run_id!r}", code="NO_SUCH_RUN")
    else:
        _check_pending(ws)
        run_id, run_dir = workspace.create_staging_run(ws, "delegate")
    raw_dir = run_dir / workspace.RAW
    raw_dir.mkdir(exist_ok=True)
    values = {
        "product_name": st.product["name"],
        "target_url": st.product["target_url"],
        "scope": st.scope.get("text") or "the whole product",
        "questions": questions.strip(),
        "allowed_urls": ", ".join(allowed_urls) if allowed_urls else "any relevant public page",
        "raw_dir": str(raw_dir),
    }
    prompt = PLACEHOLDER_RE.sub(lambda m: values.get(m.group(1), m.group(0)), block.group(1))
    leftover = sorted(set(PLACEHOLDER_RE.findall(prompt)))
    if leftover:
        raise CheckFailed(f"{prov.adapter} brief has unknown placeholders: {leftover}",
                          code="BAD_ADAPTER")  # fmt: skip
    workspace.append_history(ws, {"event": "delegate", "run_id": run_id, "provider": prov.id})
    return Delegation(
        run_id, raw_dir, cap_id, prov.id, prov.kind, prov.invoke, prompt.rstrip() + "\n"
    )
