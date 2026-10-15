#!/usr/bin/env python3.11
"""ProductForge CLI — the deterministic core behind the ``productforge`` skill.

Every subcommand accepts ``--workspace DIR``
and ``--json`` (before or after the subcommand name). Exit codes: 0 ok,
1 check failed, 2 usage error / not implemented.

Standard library only. Requires Python 3.11+; the plugin always invokes it as ``python3.11``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

MIN_PYTHON = (3, 11)
if sys.version_info < MIN_PYTHON:  # keep this file parseable by old interpreters
    found = f"{sys.version_info[0]}.{sys.version_info[1]}"
    sys.stderr.write(
        f"pf.py: ProductForge requires Python 3.11+ (found {found}). "
        "Run it with python3.11 (macOS: brew install python@3.11).\n"
    )
    sys.exit(2)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dataclasses import dataclass  # noqa: E402

from pflib import (  # noqa: E402
    __version__,
    brief,
    catalog,
    commands,
    competitors,
    config,
    deps,
    discover,
    domain,
    features,
    gates,
    merge,
    metrics,
    observe,
    plans,
    render,
    research,
    scaffold,
    score,
    state,
    summary,
    trace,
    validators,
    workflows,
    workspace,
)
from pflib.errors import (  # noqa: E402
    EXIT_CHECK_FAILED,
    EXIT_OK,
    NotImplementedPF,
    PFError,
    UsageError,
)
from pflib.index import WorkspaceIndex  # noqa: E402
from pflib.io import atomic_write_text, emit  # noqa: E402

Handler = Callable[[argparse.Namespace], Any]


@dataclass
class CommandResult:
    """A handler result with a non-zero exit code and/or custom human-readable text."""

    payload: Any
    exit_code: int = EXIT_OK
    human: str | None = None


NO_WORKSPACE = {"workspace": None, "message": "No ProductForge workspace found"}


def _cmd_init(args: argparse.Namespace) -> dict[str, Any]:
    ws, st = scaffold.init_workspace(
        args.url, out=args.out, scope=args.scope, name=args.name, force_adopt=args.force_adopt
    )
    return {
        "workspace": str(ws),
        "state": st.state.value,
        "product": st.product["name"],
        "target_url": st.product["target_url"],
        "slug": st.product["slug"],
        "our_name": st.product["our_name"],
        "needs_rename": st.product["needs_rename"],
        "scope": st.scope,
        "next_command": commands.PRIMARY_COMMAND[st.state],
    }


def _status_human(p: dict[str, Any]) -> str:
    prod, s, conf, gate = p["product"], p["summary"], p["confidence"], p["gate_progress"]
    rename = " (placeholder — rename needed)" if prod.get("needs_rename") else ""
    scope = p["scope"]
    scope_line = f"Scope: {scope['text'] or 'not set'}"
    if scope["text"] and not scope["accepted"]:
        scope_line += " (not accepted yet)"
    stale = f"   Stale: {', '.join(p['stale'])}" if p["stale"] else ""
    lines = [
        f"Product discovered: {prod['name']}  ({prod['target_url']})",
        f"Our working name: {prod['our_name']}{rename}",
        scope_line,
        f"Open stage: {p['open_stage']}{stale}"
        + (" — IMPLEMENTATION: phases are being executed" if p["implementation_detected"] else ""),
        "",
        f"Research sources discovered: {s['sources']}",
        f"Major product domains: {s['domains']}",
        f"Major features identified: {s['features']}",
        f"Core workflows identified: {s['workflows']}",
        f"Primary entities identified: {s['entities']}",
        f"Role boundaries identified: {s['roles']}",
        f"Permission rules: {s['permission_rules']}"
        + (
            f" ({s['unknown_permission_cells']} unknown cells)"
            if s["unknown_permission_cells"]
            else ""
        ),
        f"External integrations identified: {s['integrations']}",
        "",
        "Claim confidence: " + " · ".join(f"{k.title()} {v}" for k, v in conf.items()),
        f"Gate {gate['stage']}: {gate['done']}/{gate['total']} conditions passing"
        + (" — ready to advance" if gate["passed"] else ""),
        f"Next command: /productforge {p['next_command']}",
    ]
    return "\n".join(lines)


def _cmd_status(args: argparse.Namespace) -> Any:
    if args.workspace is None and workspace.find_workspace(Path.cwd()) is None:
        return NO_WORKSPACE
    ws = workspace.resolve_workspace(args.workspace)
    st = state.load(ws)
    index = WorkspaceIndex(ws)
    report = gates.evaluate(ws, st.state.value)
    done, total = report.progress
    payload = {
        "workspace": str(ws),
        "product": st.product,
        "scope": st.scope,
        "open_stage": st.state.value,
        "stale": st.stale,
        "summary": metrics.summary(ws, index),
        "counts": metrics.counts(ws, index),
        "confidence": metrics.confidence_breakdown(ws, index),
        "gate_progress": {
            "stage": report.stage,
            "passed": report.passed,
            "done": done,
            "total": total,
            "failing": report.failing(),
        },
        "next_command": commands.next_command(ws, st, report),
        "capabilities": st.capabilities,
        "implementation_detected": st.state is state.State.PHASE_PLAN_READY
        and plans.implementation_detected(ws, report.passed),
    }
    return CommandResult(payload, human=_status_human(payload))


def _cmd_check_command(args: argparse.Namespace) -> dict[str, Any]:
    ws = workspace.resolve_workspace(args.workspace)
    return commands.check_command(ws, args.cmd).to_dict()


def _cmd_advance(args: argparse.Namespace) -> CommandResult:
    ws = workspace.resolve_workspace(args.workspace)
    st = state.load(ws)
    closing = st.state
    target = state.parse_state(args.to)
    state.check_transition(st, target)
    report = gates.evaluate(ws, closing.value)
    payload: dict[str, Any] = {
        "from": closing.value,
        "to": target.value,
        "passed": report.passed,
        "transitioned": False,
        "gate": report.to_dict(),
    }
    if not report.passed:
        payload["message"] = f"{closing.value} gate failing: {', '.join(report.failing())}"
        return CommandResult(payload, EXIT_CHECK_FAILED)
    if not args.confirmed:
        payload["message"] = (
            "gate passed; show this report to the user and re-run with --confirmed once they agree"
        )
        return CommandResult(payload)
    locks = state.snapshot_locks(ws, closing)
    st.locks[closing.value] = locks
    state.transition(st, target, workspace.iso(workspace.utc_now()))
    state.save(ws, st)
    workspace.append_history(
        ws, {"event": "advance", "from": closing.value, "to": target.value, "locked": len(locks)}
    )
    payload.update(transitioned=True, open_stage=st.state.value, locked_records=len(locks))
    return CommandResult(payload)


def _cmd_reopen(args: argparse.Namespace) -> dict[str, Any]:
    ws = workspace.resolve_workspace(args.workspace)
    st = state.load(ws)
    previous = st.state.value
    stage = state.parse_state(args.state)
    stale = state.reopen(st, stage, args.reason)
    state.save(ws, st)
    workspace.append_history(
        ws,
        {
            "event": "reopen",
            "from": previous,
            "to": stage.value,
            "reason": args.reason,
            "stale": stale,
        },
    )
    return {"open_stage": st.state.value, "stale": stale, "reason": args.reason}


def _findings_human(result: dict[str, Any]) -> list[str]:
    lines = [
        f"{f['severity'].upper():5} {f['code']}  {f['artifact'] or '-'}"
        + (f" {f['record_id']}" if f["record_id"] else "")
        + f": {f['message']}"
        for f in result["findings"]
    ]
    lines.append(f"{result['errors']} error(s), {result['warnings']} warning(s)")
    return lines


def _cmd_validate(args: argparse.Namespace) -> CommandResult:
    ws = workspace.resolve_workspace(args.workspace)
    stage = state.parse_state(args.stage).value if args.stage else None
    result = validators.summary(validators.run(ws, stage=stage, artifact=args.artifact))
    code = EXIT_CHECK_FAILED if result["errors"] else EXIT_OK
    return CommandResult(result, code, human="\n".join(_findings_human(result)))


def _cmd_check(args: argparse.Namespace) -> CommandResult:
    ws = workspace.resolve_workspace(args.workspace)
    st = state.load(ws)
    result = validators.summary(validators.run(ws))
    report = gates.evaluate(ws, st.state.value)
    payload: dict[str, Any] = {"validate": result, "gate": report.to_dict()}
    if st.state is state.State.PHASE_PLAN_READY:
        payload["lint"] = plans.report(ws)
    done, total = report.progress
    human = _findings_human(result) + [
        f"Gate {report.stage}: {done}/{total} conditions passing"
        + ("" if report.passed else f" (failing: {', '.join(report.failing())})")
    ]
    code = EXIT_CHECK_FAILED if result["errors"] else EXIT_OK
    return CommandResult(payload, code, human="\n".join(human))


def _optional_workspace(explicit: str | None) -> Path | None:
    if explicit:
        return workspace.resolve_workspace(explicit)
    return workspace.find_workspace(Path.cwd())


def _cmd_deps(args: argparse.Namespace) -> Any:
    action, rest = args.action, args.args or []

    def need(n: int, usage: str) -> None:
        if len(rest) != n:
            raise UsageError(f"usage: pf.py deps {usage}", code="USAGE_ERROR")

    if action == "check":
        need(0, "check [--available a,b,c]")
        available = {a.strip() for a in (args.available or "").split(",") if a.strip()}
        result = deps.check(_optional_workspace(args.workspace), available)
        lines = [
            f"{cap:15} → {res['provider']}"
            + (f" {res['version']}" if res["version"] else "")
            + (" (pinned)" if res["pinned"] else "")
            + (f"   installable: {', '.join(res['installable'])}" if res["installable"] else "")
            + (f"   note: {res['note']}" if res["note"] else "")
            for cap, res in result["capabilities"].items()
        ]
        if result["offer"]:
            lines.append(f"offer installs for: {', '.join(result['offer'])}")
        return CommandResult(result, human="\n".join(lines))
    if action == "install":
        need(1, "install <capability|provider> [--scope S] [--confirmed] [--ack-third-party]")
        payload, code = deps.install(
            _optional_workspace(args.workspace), rest[0], args.scope, args.confirmed,
            args.ack_third_party,
        )  # fmt: skip
        return CommandResult(payload, code)
    ws = workspace.resolve_workspace(args.workspace)
    if action == "use":
        need(2, "use <capability> <provider>")
        return deps.use(ws, rest[0], rest[1])
    if not rest:
        raise UsageError("usage: pf.py deps offered <capability>...", code="USAGE_ERROR")
    return deps.mark_offered(ws, rest)


def _cmd_delegate(args: argparse.Namespace) -> CommandResult:
    ws = workspace.resolve_workspace(args.workspace)
    result = brief.render_delegation(
        ws, args.provider, args.task, allowed_urls=args.allowed_url, run_id=args.run_id
    )
    return CommandResult(result.to_dict(), human=result.prompt)


def _cmd_discover(args: argparse.Namespace) -> CommandResult:
    ws = _optional_workspace(args.workspace)
    target_url, host = scaffold.parse_target(args.url)
    slug = state.load(ws).product["slug"] if ws else scaffold.slug_from_host(host)
    max_pages = args.max_pages or int(config.resolve("research.max_pages_per_domain", ws))
    result = discover.discover(
        target_url,
        user_agent=str(config.resolve("research.user_agent", ws)),
        delay=float(config.resolve("research.request_delay_seconds", ws)),
        max_pages_per_host=max_pages,
        slug=slug,
    )
    cache = str(discover.write_cache(ws, result)) if ws else None
    payload = {
        "host": result.host,
        "counts": result.counts(),
        "candidates": len(result.entries),
        "external_links": len(result.external),
        "disallowed": result.disallowed,
        "truncated": result.truncated,
        "errors": len(result.errors),
        "requests": result.requests,
        "probes": result.probes,
        "cache": cache,
    }
    if ws is None:
        payload["entries"] = result.entries
        payload["external"] = result.external
    human = [
        f"{result.host}: {len(result.entries)} candidate URLs, {result.disallowed} disallowed "
        f"by robots.txt, {len(result.errors)} errors, {result.requests} requests"
    ]
    human += [f"  {cat:20} {n}" for cat, n in result.counts().items()]
    if cache:
        human.append(f"cache: {cache}")
    return CommandResult(payload, human="\n".join(human))


def _cmd_research_plan(args: argparse.Namespace) -> dict[str, Any]:
    ws = workspace.resolve_workspace(args.workspace)
    return research.plan(ws)


def _cmd_feature_plan(args: argparse.Namespace) -> dict[str, Any]:
    ws = workspace.resolve_workspace(args.workspace)
    return features.plan(ws)


def _cmd_workflow_candidates(args: argparse.Namespace) -> dict[str, Any]:
    ws = workspace.resolve_workspace(args.workspace)
    return workflows.candidates(ws)


def _cmd_permission_gaps(args: argparse.Namespace) -> dict[str, Any]:
    ws = workspace.resolve_workspace(args.workspace)
    index = WorkspaceIndex(ws)
    cells = domain.permission_cells(index)
    total = sum(cells["cells"].values()) + cells["missing"]
    unknown = cells["cells"]["?"]
    limit = float(config.resolve("model.max_unknown_permission_ratio", ws))
    ratio = round(unknown / total, 3) if total else 0.0
    return {
        "cells": total,
        "unknown": unknown,
        "ratio": ratio,
        "max_ratio": limit,
        "over_limit": ratio > limit,
        "gaps": domain.permission_gaps(index),
    }


def _cmd_competitor_candidates(args: argparse.Namespace) -> dict[str, Any]:
    ws = workspace.resolve_workspace(args.workspace)
    return competitors.candidates(ws)


def _add_score(p: argparse.ArgumentParser) -> None:
    p.add_argument("--write", action="store_true", help="re-render the views built from scores")


def _cmd_score(args: argparse.Namespace) -> dict[str, Any]:
    ws = workspace.resolve_workspace(args.workspace)
    out = score.report(ws)
    if args.write:
        out["rendered"] = render.render_all(ws)
    return out


def _add_override(p: argparse.ArgumentParser) -> None:
    p.add_argument("feature", help="feature ID, e.g. F-012")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--decision", choices=score.DECISIONS)
    group.add_argument("--clear", action="store_true", help="remove the override")
    p.add_argument("--reason", required=True, help="the user's reason, in their words")


def _cmd_override(args: argparse.Namespace) -> dict[str, Any]:
    ws = workspace.resolve_workspace(args.workspace)
    return score.record_override(ws, args.feature, None if args.clear else args.decision,
                                 args.reason)  # fmt: skip


def _add_set_preferences(p: argparse.ArgumentParser) -> None:
    p.add_argument("--stack", help='comma-separated stack preferences, e.g. "Next.js, PostgreSQL"')
    p.add_argument("--deployment", choices=("docker", "serverless", "k8s"))


def _cmd_set_preferences(args: argparse.Namespace) -> dict[str, Any]:
    ws = workspace.resolve_workspace(args.workspace)
    values: dict[str, Any] = {}
    if args.stack is not None:
        values["architecture.preferences"] = [s.strip() for s in args.stack.split(",") if s.strip()]
    if args.deployment is not None:
        values["architecture.deployment_target"] = args.deployment
    if values:  # without arguments: just report what is stored
        config.write_config(ws, values)
    keys = ("architecture.preferences", "architecture.deployment_target")
    return {"architecture": {k.split(".", 1)[1]: config.resolve(k, ws) for k in keys}}


def _cmd_lint_phases(args: argparse.Namespace) -> CommandResult:
    ws = workspace.resolve_workspace(args.workspace)
    out = plans.report(ws)
    human = [
        f"{f['severity'].upper():5} {f['code']}  {f['artifact']}: {f['message']}"
        for f in out["findings"]
    ]
    human += [
        f"Phase {p['number']} — {p['name']} (depends on {', '.join(p['depends_on']) or 'none'})"
        for p in out["phases"]
    ]
    human.append(f"{out['errors']} error(s), {out['warnings']} warning(s)")
    return CommandResult(
        out, EXIT_CHECK_FAILED if out["errors"] else EXIT_OK, human="\n".join(human)
    )


OBSERVE_ACTIONS = ("consent", "start", "status", "stop", "ingest", "discard")


def _add_observe(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=OBSERVE_ACTIONS, help="observe-mode action")
    p.add_argument(
        "session",
        nargs="?",
        help="session ID (status/stop: default latest; ingest/discard: required)",
    )
    p.add_argument("--confirmed", action="store_true", help="the user agreed (consent)")
    p.add_argument("--url", help="start: the page to open (default: the target URL)")
    p.add_argument("--label", help="start: what the user is about to do")
    p.add_argument("--role", help="start: the role of the account the user signs in with")
    p.add_argument("--port", type=int, help="start: control-panel port (default: observe.port)")
    p.add_argument("--reason", help="discard: why the session's raw files are deleted")


def _cmd_observe(args: argparse.Namespace) -> dict[str, Any]:
    ws = workspace.resolve_workspace(args.workspace)
    if args.action == "consent":
        return observe.record_consent(ws, args.confirmed)
    if args.action == "start":
        return observe.start(ws, url=args.url, label=args.label, port=args.port, role=args.role)
    if args.action == "status":
        return observe.session_status(ws, args.session)
    if args.action == "stop":
        return observe.stop(ws, args.session)
    if not args.session:
        raise UsageError(f"observe {args.action} needs a session ID", code="OBSERVE_NO_SESSION")
    if args.action == "ingest":
        return observe.ingest(ws, args.session)
    return observe.discard(ws, args.session, args.reason)


def _cmd_render(args: argparse.Namespace) -> dict[str, Any]:
    ws = workspace.resolve_workspace(args.workspace)
    return {"rendered": render.render_all(ws, only=args.artifact)}


def _add_render(p: argparse.ArgumentParser) -> None:
    p.add_argument("--artifact", metavar="PATH", help="only this artifact")


def _cmd_set_scope(args: argparse.Namespace) -> dict[str, Any]:
    ws = workspace.resolve_workspace(args.workspace)
    st = scaffold.set_scope(ws, args.text, accepted=args.accepted, source=args.source)
    return {"scope": st.scope}


def _cmd_next_id(args: argparse.Namespace) -> dict[str, Any]:
    ws = workspace.resolve_workspace(args.workspace)
    return {"id": merge.allocate_next(ws, args.prefix)}


def _cmd_staging(args: argparse.Namespace) -> dict[str, Any]:
    ws = workspace.resolve_workspace(args.workspace)
    if args.action == "list":
        return {"pending": workspace.pending_runs(ws)}
    if args.action == "discard":
        if not args.run_id or not args.reason:
            raise UsageError(
                "usage: pf.py staging discard <run-id> --reason TEXT", code="USAGE_ERROR"
            )
        return {
            "discarded": args.run_id,
            "path": str(workspace.discard_run(ws, args.run_id, args.reason)),
        }
    if not args.role:
        raise UsageError("usage: pf.py staging new --role ROLE", code="USAGE_ERROR")
    run_id, path = workspace.create_staging_run(ws, args.role)
    return {"run_id": run_id, "path": str(path)}


def _cmd_merge(args: argparse.Namespace) -> Any:
    ws = workspace.resolve_workspace(args.workspace)
    if args.check:
        result = merge.preflight(ws, args.run_id)
        return CommandResult(result, EXIT_OK if result["ok"] else EXIT_CHECK_FAILED)
    return merge.merge(ws, args.run_id).to_dict()


def _cmd_brief(args: argparse.Namespace) -> CommandResult:
    ws = workspace.resolve_workspace(args.workspace)
    result = brief.render(
        ws,
        role=args.role,
        task=args.task,
        partition=args.partition,
        inputs=args.input,
        templates=args.template,
        budget=args.budget,
        run_id=args.run_id,
    )
    return CommandResult(result.to_dict(), human=result.text)


def _not_implemented(name: str, phase: str) -> Handler:
    def handler(args: argparse.Namespace) -> Any:
        raise NotImplementedPF(f"{name}: not implemented (phase {phase})")

    return handler


def _add_init(p: argparse.ArgumentParser) -> None:
    p.add_argument("url", help="public product URL")
    p.add_argument("--scope", help="optional scope, e.g. 'issue tracking'")
    p.add_argument("--out", help="output workspace directory (default ./<product-slug>/)")
    p.add_argument("--name", help="working name for OUR product (never the target's name)")
    p.add_argument("--force-adopt", action="store_true", help="initialise inside a non-empty dir")


def _add_deps(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "action", nargs="?", default="check", choices=["check", "install", "use", "offered"],
        help="check (default) | install <target> | use <capability> <provider> | offered <cap>...",
    )  # fmt: skip
    p.add_argument("args", nargs="*", help="arguments of the action")
    p.add_argument("--available", help="comma list of skills/agents the host session can see")
    p.add_argument("--scope", help="install scope: project (default), user or local")
    p.add_argument("--confirmed", action="store_true", help="the user explicitly agreed to install")
    p.add_argument(
        "--ack-third-party", action="store_true", help="user accepted a third-party source"
    )


def _add_delegate(p: argparse.ArgumentParser) -> None:
    p.add_argument("provider", help="provider id from capabilities.json")
    p.add_argument("--task", required=True, help="the questions the provider must answer")
    p.add_argument(
        "--allowed-url", action="append", help="URL or site the provider may use (repeat)"
    )
    p.add_argument("--run-id", help="reuse an existing staging run")


def _add_set_scope(p: argparse.ArgumentParser) -> None:
    p.add_argument("text", help="scope, e.g. 'issue tracking'")
    p.add_argument("--accepted", action="store_true", help="the user accepted this scope")
    p.add_argument("--source", choices=state.SCOPE_SOURCES, default="user", help="who chose it")


def _add_check_command(p: argparse.ArgumentParser) -> None:
    p.add_argument("cmd", help="productforge command, e.g. features")


def _add_advance(p: argparse.ArgumentParser) -> None:
    p.add_argument("--to", required=True, metavar="STATE", help="next lifecycle state")
    p.add_argument("--confirmed", action="store_true", help="the user confirmed the gate report")


def _add_reopen(p: argparse.ArgumentParser) -> None:
    p.add_argument("state", metavar="STATE", help="earlier stage to re-open")
    p.add_argument("--reason", required=True, help="why the stage is re-opened")


def _add_next_id(p: argparse.ArgumentParser) -> None:
    p.add_argument("prefix", help="record prefix, e.g. D")


def _add_staging(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=["new", "list", "discard"], help="staging action")
    p.add_argument("run_id", nargs="?", help="run to discard")
    p.add_argument("--role", help="role agent that will write the run (new)")
    p.add_argument("--reason", help="why the run is discarded (discard)")


def _add_merge(p: argparse.ArgumentParser) -> None:
    p.add_argument("run_id", help="staging run id")
    p.add_argument(
        "--check", action="store_true", help="preflight: merge into a scratch copy and validate"
    )


def _add_brief(p: argparse.ArgumentParser) -> None:
    p.add_argument("--role", required=True, help="role agent, e.g. research-agent")
    p.add_argument("--task", required=True, help="what the agent must do")
    p.add_argument("--partition", help="this run's slice of the work (parallel runs)")
    p.add_argument("--input", action="append", help="workspace file the agent must read (repeat)")
    p.add_argument("--template", action="append", help="template to fill, e.g. research/sources.md")
    p.add_argument("--budget", help="e.g. 'at most 15 sources'")
    p.add_argument("--run-id", help="existing run: render a repair brief with preflight findings")


def _add_validate(p: argparse.ArgumentParser) -> None:
    p.add_argument("--stage", metavar="STATE", help="only this stage's artifacts")
    p.add_argument("--artifact", metavar="PATH", help="only this artifact")


def _add_discover(p: argparse.ArgumentParser) -> None:
    p.add_argument("url", help="root URL to reconnoitre")
    p.add_argument("--max-pages", type=int, help="crawl cap per host")


def _add_trace(p: argparse.ArgumentParser) -> None:
    p.add_argument("--write", action="store_true", help="render spec/TRACEABILITY.md")


def _add_nothing(p: argparse.ArgumentParser) -> None:
    return None


def _add_explain(p: argparse.ArgumentParser) -> None:
    p.add_argument("id", help='a record ID (R-007) or a phase ("Phase 09")')


def _add_complete(p: argparse.ArgumentParser) -> None:
    p.add_argument("--confirmed", action="store_true", help="the user agreed")


def _cmd_trace(args: argparse.Namespace) -> CommandResult:
    ws = workspace.resolve_workspace(args.workspace)
    out = trace.report(ws)
    if args.write:
        target = ws / catalog.TRACEABILITY_PATH
        if not target.is_file():
            seeded = scaffold.seed_text(ws, catalog.TRACEABILITY_PATH)
            atomic_write_text(target, seeded or "# Traceability\n")
        out["rendered"] = render.render_all(ws, only=catalog.TRACEABILITY_PATH)
    human = [f"{f['severity'].upper():5} {f['code']}  {f['record_id'] or f['artifact']}: "
             f"{f['message']}" for f in out["findings"]]  # fmt: skip
    human.append(f"{out['fully_traced']}/{out['requirements']} requirements traced from a source "
                 f"to a phase; {out['errors']} error(s), {out['warnings']} warning(s)")  # fmt: skip
    return CommandResult(
        out, EXIT_CHECK_FAILED if out["errors"] else EXIT_OK, human="\n".join(human)
    )


def _cmd_explain(args: argparse.Namespace) -> CommandResult:
    ws = workspace.resolve_workspace(args.workspace)
    out = trace.explain(ws, args.id)
    g = trace.build(ws)

    def lines(nodes: list[dict[str, Any]], arrow: str, depth: int = 1) -> list[str]:
        rows = []
        for n in nodes:
            rows.append(f"{'  ' * depth}{arrow} {trace.describe(n['id'], g.records)}  [{n['via']}]")
            rows += lines(n["children"], arrow, depth + 1)
        return rows

    human = [trace.describe(args.id, g.records), "upstream (rests on):"] + lines(
        out["upstream"], "←"
    )
    human += ["downstream (built by):"] + lines(out["downstream"], "→")
    return CommandResult(out, human="\n".join(human))


def _cmd_publish_summary(args: argparse.Namespace) -> CommandResult:
    ws = workspace.resolve_workspace(args.workspace)
    text = summary.markdown(ws)
    return CommandResult({"markdown": text}, human=text.rstrip("\n"))


def _cmd_complete(args: argparse.Namespace) -> CommandResult:
    ws = workspace.resolve_workspace(args.workspace)
    st = state.load(ws)
    report = gates.evaluate(ws, st.state.value)
    payload: dict[str, Any] = {"completed": False, "gate": report.to_dict()}
    if st.state is not state.State.PHASE_PLAN_READY:
        raise UsageError(f"complete applies to PHASE_PLAN_READY (open: {st.state.value})",
                         code="ILLEGAL_TRANSITION")  # fmt: skip
    if not report.passed:
        payload["message"] = f"PHASE_PLAN_READY gate failing: {', '.join(report.failing())}"
        return CommandResult(payload, EXIT_CHECK_FAILED)
    if not args.confirmed:
        payload["message"] = "gate passed; re-run with --confirmed once the user agrees"
        return CommandResult(payload)
    now = workspace.iso(workspace.utc_now())
    state.complete(st, now)
    state.save(ws, st)
    workspace.append_history(ws, {"event": "complete", "stage": st.state.value})
    payload.update(completed=True, completed_at=now)
    return CommandResult(payload)


# name, help, argument builder, handler
SUBCOMMANDS: list[tuple[str, str, Callable[[argparse.ArgumentParser], None], Handler]] = [
    ("init", "create a workspace and open DISCOVERY", _add_init, _cmd_init),
    ("status", "counts, open stage, gate progress, next command", _add_nothing, _cmd_status),
    (
        "check-command",
        "is a productforge command allowed now?",
        _add_check_command,
        _cmd_check_command,
    ),
    ("advance", "pass the open stage's gate and transition", _add_advance, _cmd_advance),
    ("reopen", "re-open an earlier stage (feedback loop)", _add_reopen, _cmd_reopen),
    ("set-scope", "record the product scope", _add_set_scope, _cmd_set_scope),
    ("next-id", "allocate one record ID", _add_next_id, _cmd_next_id),
    ("staging", "manage agent staging runs", _add_staging, _cmd_staging),
    ("merge", "merge a staging run into canonical files", _add_merge, _cmd_merge),
    ("brief", "render the brief for one agent run", _add_brief, _cmd_brief),
    (
        "delegate",
        "render a delegated provider prompt (capability adapters)",
        _add_delegate,
        _cmd_delegate,
    ),
    ("deps", "detect, install (with consent) or pin capability providers", _add_deps, _cmd_deps),
    (
        "validate",
        "schema, references, confidence and locks",
        _add_validate,
        _cmd_validate,
    ),
    (
        "discover",
        "robots/sitemap/link reconnaissance",
        _add_discover,
        _cmd_discover,
    ),
    (
        "research-plan",
        "partitions, budgets, coverage and scope advice for research",
        _add_nothing,
        _cmd_research_plan,
    ),
    (
        "feature-plan",
        "domains, features per domain, surfaces without features",
        _add_nothing,
        _cmd_feature_plan,
    ),
    ("render", "re-render generated views from records", _add_render, _cmd_render),
    (
        "workflow-candidates",
        "propose workflows to reconstruct (deterministic)",
        _add_nothing,
        _cmd_workflow_candidates,
    ),
    (
        "permission-gaps",
        "unknown permission cells, their unknowns and the share over the limit",
        _add_nothing,
        _cmd_permission_gaps,
    ),
    (
        "competitor-candidates",
        "competitor names found in comparison/review sources (users confirm)",
        _add_nothing,
        _cmd_competitor_candidates,
    ),
    ("score", "compute feature priorities and decisions", _add_score, _cmd_score),
    ("observe", "observe mode: consent, sessions, ingestion", _add_observe, _cmd_observe),
    (
        "set-preferences",
        "store stack preferences for /productforge architect",
        _add_set_preferences,
        _cmd_set_preferences,
    ),
    (
        "override",
        "record the user's decision for a feature (amends its score card)",
        _add_override,
        _cmd_override,
    ),
    (
        "lint-phases",
        "lint generated phase plans",
        _add_nothing,
        _cmd_lint_phases,
    ),
    ("trace", "build the traceability graph", _add_trace, _cmd_trace),
    ("explain", "show a record's upstream and downstream chain", _add_explain, _cmd_explain),
    ("complete", "record that PHASE_PLAN_READY is complete", _add_complete, _cmd_complete),
    (
        "publish-summary",
        "a shareable blueprint summary (counts, funnel, decisions, phases)",
        _add_nothing,
        _cmd_publish_summary,
    ),
    ("check", "validate + gate + lint + trace", _add_nothing, _cmd_check),
]


def _global_options(parser: argparse.ArgumentParser, suppress: bool) -> None:
    # Subparsers re-declare the globals with SUPPRESS defaults so `pf.py status --json`
    # and `pf.py --json status` both work without the subparser clobbering the value.
    default_ws: Any = argparse.SUPPRESS if suppress else None
    default_json: Any = argparse.SUPPRESS if suppress else False
    parser.add_argument(
        "--workspace",
        metavar="DIR",
        default=default_ws,
        help="workspace directory (default: nearest ancestor with .productforge/)",
    )
    parser.add_argument(
        "--json", action="store_true", default=default_json, help="machine-readable JSON output"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pf.py",
        description="ProductForge deterministic core.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    _global_options(parser, suppress=False)
    sub = parser.add_subparsers(dest="command", metavar="<subcommand>")
    sub.required = True
    for name, help_text, add_args, handler in SUBCOMMANDS:
        p = sub.add_parser(name, help=help_text, description=help_text)
        _global_options(p, suppress=True)
        add_args(p)
        p.set_defaults(handler=handler)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.handler(args)
    except PFError as exc:
        if args.json:
            emit(exc.to_dict(), as_json=True)
        print(f"pf.py: {exc.message}", file=sys.stderr)
        return exc.exit_code
    if not isinstance(result, CommandResult):
        result = CommandResult(result)
    if result.human is not None and not args.json:
        print(result.human)
    else:
        emit(result.payload, as_json=args.json)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
