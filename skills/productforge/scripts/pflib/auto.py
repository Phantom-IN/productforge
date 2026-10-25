"""The autonomous driver: one headless ``claude -p`` session per stage command.

Golden rule 9: this module and ``deps``/``capabilities``/``observe`` are the only ones that start
processes, and this one starts only ``claude -p`` sessions, only after ``pf.py auto start
--confirmed`` (the typed flag is the consent). The loop reads state through an injected ``pf``
callable (in-process in ``pf.py``), so it never shells out to ``pf.py`` itself. The runner and the
sleep function are injected too, so tests never start a process or wait.

Loop: status -> (PHASE_PLAN_READY and gate passed: ``complete --auto``, stop) -> ``check-command``
(``needs_transition``: ``advance --auto``; ``refused``: stop) -> one session -> compare
fingerprints. Stops: stall, retry limit, session limit, refusal, stop file, missing ``claude``.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pflib import autonomy, config, workspace
from pflib.errors import UsageError

LOG_FILE = "auto.log"
SESSION_LOG = "auto-session.log"
STOP_FILE = "auto.stop"
FALLBACK_SOURCES_CEILING = 400  # used only while `auto.max_sources_ceiling` is not registered
WORKFLOWS_CAP_KEY = "model.max_workflows"

PfCall = Callable[[list[str]], tuple[int, dict[str, Any]]]
Runner = Callable[..., Any]
Sleep = Callable[[float], None]

_KNOBS = (
    "main_model",
    "subagent_model",
    "permission_args",
    "max_sessions",
    "max_stalls",
    "retry_wait_seconds",
    "max_retries",
    "parallel_runs",
)


def plugin_root() -> Path:
    """The nearest parent of this file holding ``.claude-plugin/plugin.json``, else the env."""
    for parent in Path(__file__).resolve().parents:
        if (parent / ".claude-plugin" / "plugin.json").is_file():
            return parent
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env and (Path(env) / ".claude-plugin" / "plugin.json").is_file():
        return Path(env)
    raise UsageError(
        "cannot locate the plugin root (.claude-plugin/plugin.json); set CLAUDE_PLUGIN_ROOT",
        code="PLUGIN_ROOT_NOT_FOUND",
    )


def load_cfg(ws: Path, stack: str | None = None) -> dict[str, Any]:
    """Resolve every ``auto.*`` knob (CLI is not involved: config.json -> defaults)."""
    cfg: dict[str, Any] = {k: config.resolve(f"auto.{k}", ws) for k in _KNOBS}
    ceiling_key = "auto.max_sources_ceiling"
    cfg["max_sources_ceiling"] = (
        config.resolve(ceiling_key, ws)
        if ceiling_key in config.DEFAULTS
        else FALLBACK_SOURCES_CEILING
    )
    cfg["max_workflows_ceiling"] = config.resolve("auto.max_workflows_ceiling", ws)
    cfg["claude_bin"] = config.resolve("capabilities.claude_bin", ws)
    cfg["stack"] = stack or None
    return cfg


BAD_STACK_CHARS = ('"', "'", "`", "\n", "\r")
SLEEP_STEP = 15.0  # longest uninterrupted sleep: the stop file is polled between steps
REPEATED_FAILURE = 3  # the same non-zero rc this many times in a row is fatal


def check_stack(stack: str | None) -> None:
    """The stack text goes into a prompt string: no quotes, backticks or line breaks."""
    if stack and any(c in stack for c in BAD_STACK_CHARS):
        raise UsageError(
            "--stack must not contain quotes, backticks or line breaks", code="USAGE_ERROR"
        )


def session_command(ws: Path, cmd: str, cfg: dict[str, Any]) -> list[str]:
    """``claude -p "/productforge <cmd>" --plugin-dir <root> --model <m> <permission args>``."""
    prompt = f"/productforge {cmd}"
    if cmd == "architect" and cfg.get("stack"):
        check_stack(cfg["stack"])
        prompt += f' --stack "{cfg["stack"]}"'
    return [
        cfg.get("claude_bin") or "claude",
        "-p",
        prompt,
        "--plugin-dir",
        str(cfg.get("plugin_root") or plugin_root()),
        "--model",
        cfg["main_model"],
        *cfg["permission_args"],
    ]


def session_env(cfg: dict[str, Any], base: dict[str, str] | None = None) -> dict[str, str]:
    return {
        **(os.environ if base is None else base),
        "CLAUDE_CODE_SUBAGENT_MODEL": cfg["subagent_model"],
    }


def fingerprint(status: dict[str, Any]) -> str:
    """Open stage, record counts and gate progress: what a productive session changes."""
    gate = status.get("gate_progress") or {}
    parts = {
        "open_stage": status.get("open_stage"),
        "counts": status.get("counts"),
        "gate": [gate.get("done"), gate.get("total"), gate.get("failing")],
    }
    return json.dumps(parts, sort_keys=True)


# -- files ---------------------------------------------------------------------------------------
def log_path(ws: Path) -> Path:
    return workspace.pf_dir(ws) / LOG_FILE


def stop_path(ws: Path) -> Path:
    return workspace.pf_dir(ws) / STOP_FILE


def log_event(ws: Path, event: str, **fields: Any) -> None:
    entry = {"at": workspace.iso(workspace.utc_now()), "event": event, **fields}
    with open(log_path(ws), "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_log(ws: Path, last: int | None = None) -> list[dict[str, Any]]:
    path = log_path(ws)
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue  # a torn or hand-edited line never breaks `auto status`
        if isinstance(row, dict):
            rows.append(row)
    return rows[-last:] if last else rows


def request_stop(ws: Path) -> Path:
    path = stop_path(ws)
    path.write_text(workspace.iso(workspace.utc_now()) + "\n", encoding="utf-8")
    return path


# -- knobs applied for the run ---------------------------------------------------------------------
def apply_parallelism(ws: Path, cfg: dict[str, Any]) -> dict[str, int]:
    """Raise (never lower) the parallel-batch knobs to ``auto.parallel_runs`` for this run."""
    wanted = int(cfg["parallel_runs"])
    changes: dict[str, int] = {}
    for key in ("agents.max_pending_runs", "features.max_parallel_domains"):
        if int(config.resolve(key, ws)) < wanted:
            changes[key] = wanted
    if changes:
        config.write_config(ws, changes)
    return changes


def raise_budget(ws: Path, plan: dict[str, Any], cfg: dict[str, Any]) -> int | None:
    """Raise ``research.max_sources`` by ``budget_needed``, never above the ceiling."""
    needed = int(plan.get("budget_needed") or 0)
    if needed <= 0:
        return None
    current = int(config.resolve("research.max_sources", ws))
    target = min(current + needed, int(cfg["max_sources_ceiling"]))
    if target <= current:
        return None
    config.write_config(ws, {"research.max_sources": target})
    autonomy.decide(
        ws,
        "Raise research.max_sources for the in-scope candidates?",
        f"research.max_sources {current} -> {target}",
        f"budget_needed {needed}, ceiling {cfg['max_sources_ceiling']}",
        "research",
    )
    log_event(ws, "budget", command="research", frm=current, to=target)
    return target


def raise_workflow_cap(ws: Path, payload: dict[str, Any], cfg: dict[str, Any]) -> int | None:
    """Raise ``model.max_workflows`` to ``effective_cap`` when it cannot cover every core domain."""
    if not payload.get("cap_below_required"):
        return None
    current = int(config.resolve(WORKFLOWS_CAP_KEY, ws))
    target = min(int(payload.get("effective_cap") or 0), int(cfg["max_workflows_ceiling"]))
    if target <= current:
        return None
    reason = (
        f"{payload['cap_below_required']} core domain(s) need a workflow, ceiling "
        f"{cfg['max_workflows_ceiling']}"
    )
    config.set_value(ws, WORKFLOWS_CAP_KEY, str(target), f"auto: {reason}")
    autonomy.decide(
        ws,
        "Raise model.max_workflows so every core domain gets a workflow?",
        f"{WORKFLOWS_CAP_KEY} {current} -> {target}",
        reason,
        "workflows",
    )
    log_event(
        ws, "config-raise", command="workflows", key=WORKFLOWS_CAP_KEY, frm=current, to=target
    )
    return target


# -- the loop ------------------------------------------------------------------------------------
def next_steps(ws: Path) -> str:
    for name in ("ORCHESTRATOR_PROMPT.md", "STARTUP_PROMPT.md"):
        if (ws / name).is_file():
            return f"open Claude Code in {ws} and paste {name}"
    return f"open Claude Code in {ws} and read README.md"


def run(
    ws: Path,
    cfg: dict[str, Any],
    pf: PfCall,
    runner: Runner = subprocess.run,
    sleep: Sleep = time.sleep,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Drive the workspace to a completed plan. Returns the summary (``completed``, ``stopped``)."""
    summary: dict[str, Any] = {
        "completed": False,
        "stopped": None,
        "stages_passed": [],
        "sessions": 0,
        "retries": 0,
        "stalls": 0,
        "dry_run": dry_run,
    }
    if not dry_run:
        stop_path(ws).unlink(missing_ok=True)
        applied = apply_parallelism(ws, cfg)
        log_event(ws, "start", applied=applied)
    env = session_env(cfg)

    def finish(reason: str | None, status: dict[str, Any] | None = None) -> dict[str, Any]:
        summary["stopped"] = reason
        if status is None:
            status = pf(["status"])[1]
        summary["final_state"] = status.get("open_stage")
        summary["decisions"] = autonomy.count_decisions(ws)
        summary["next_step"] = (
            next_steps(ws) if summary["completed"] else "re-run `pf.py auto start` to resume"
        )
        if not dry_run:
            log_event(ws, "stop" if reason else "done", reason=reason, **_counts(summary))
        return summary

    def loop() -> dict[str, Any]:
        fails = 0
        last_rc: int | None = None
        same_rc = 0
        stalls = 0
        while True:
            if not dry_run and stop_path(ws).is_file():
                return finish("stop file present (pf.py auto stop)")
            status = pf(["status"])[1]
            stage = status.get("open_stage")
            gate = status.get("gate_progress") or {}
            cmd = status.get("next_command")
            fp = fingerprint(status)
            if not stage or not cmd:
                return finish("pf.py status failed", status)

            if stage == "PHASE_PLAN_READY" and gate.get("passed"):
                if dry_run:
                    summary["next"] = "complete --auto"
                    return finish(None, status)
                rc, out = pf(["complete", "--auto"])
                log_event(ws, "auto-complete", command="complete", rc=rc, fingerprint=fp)
                if rc != 0 or not out.get("completed"):
                    return finish(f"complete refused: {out.get('message') or out.get('error')}")
                summary["completed"] = True
                return finish(None, status)

            decision = pf(["check-command", cmd])[1]
            verdict = decision.get("verdict")
            if verdict == "needs_transition":
                target = decision.get("target_stage")
                if dry_run:
                    summary["next"] = f"advance --to {target} --auto"
                    return finish(None, status)
                rc, out = pf(["advance", "--to", str(target), "--auto"])
                log_event(
                    ws, "auto-advance", command=cmd, rc=rc, fingerprint=fp, frm=stage, to=target
                )
                if rc != 0 or not out.get("transitioned"):
                    return finish(f"advance to {target} refused: {out.get('message') or out}")
                summary["stages_passed"].append(stage)
                stalls = 0
                continue
            if verdict != "allowed":
                log_event(ws, "refused", command=cmd, reason=decision.get("reason"))
                return finish(f"command {cmd} refused: {decision.get('reason')}")

            if stage == "DISCOVERY" and not dry_run:
                raise_budget(ws, pf(["research-plan"])[1], cfg)

            if stage == "PRODUCT_MODEL" and not dry_run:
                raise_workflow_cap(ws, pf(["workflow-candidates"])[1], cfg)

            argv = session_command(ws, cmd, cfg)
            if dry_run:
                summary["next"] = " ".join(_quote(a) for a in argv)
                summary["next_session"] = argv
                return finish(None, status)
            if summary["sessions"] >= int(cfg["max_sessions"]):
                return finish(f"session limit reached ({cfg['max_sessions']} sessions)")

            summary["sessions"] += 1
            log_event(ws, "session", command=cmd, fingerprint=fp, n=summary["sessions"])
            try:
                with open(workspace.pf_dir(ws) / SESSION_LOG, "a", encoding="utf-8") as out_log:
                    proc = runner(
                        argv,
                        cwd=str(ws),
                        env=env,
                        stdout=out_log,
                        stderr=subprocess.STDOUT,
                        check=False,
                    )
                rc = int(proc.returncode)
            except FileNotFoundError:
                log_event(ws, "error", command=cmd, rc=127, reason=f"{argv[0]} not found")
                return finish(
                    f"{argv[0]} not found; install Claude Code or set capabilities.claude_bin"
                )
            except OSError as exc:
                log_event(ws, "error", command=cmd, rc=126, reason=f"{argv[0]}: {exc}")
                return finish(f"cannot start {argv[0]}: {exc}")

            if rc != 0:
                summary["retries"] += 1
                fails += 1
                same_rc = same_rc + 1 if rc == last_rc else 1
                last_rc = rc
                log_event(ws, "retry", command=cmd, rc=rc, n=summary["retries"])
                if fails > int(cfg["max_retries"]):
                    return finish(f"retry limit reached ({cfg['max_retries']} failed sessions)")
                if same_rc >= REPEATED_FAILURE:
                    return finish(f"repeated failure rc={rc}")
                if _wait(ws, float(cfg["retry_wait_seconds"]), sleep):
                    return finish("stop file present (pf.py auto stop)")
                continue
            fails, last_rc, same_rc = 0, None, 0

            after = fingerprint(pf(["status"])[1])
            log_event(ws, "session-done", command=cmd, rc=rc, fingerprint=after)
            if after == fp:
                stalls += 1
                summary["stalls"] += 1
                if stalls >= int(cfg["max_stalls"]):
                    log_event(ws, "stall", command=cmd, fingerprint=after)
                    return finish(
                        f"stalled: /productforge {cmd} made no progress in {stalls} sessions; read "
                        f"{workspace.pf_dir(ws) / SESSION_LOG} and run it by hand"
                    )
            else:
                stalls = 0

    try:
        return loop()
    except Exception as exc:  # the log must say why the driver died
        if not dry_run:
            log_event(ws, "stop", reason=f"error: {type(exc).__name__}: {exc}", **_counts(summary))
        raise


def _wait(ws: Path, seconds: float, sleep: Sleep) -> bool:
    """Sleep ``seconds`` in steps of at most ``SLEEP_STEP``; True when a stop was requested."""
    remaining = seconds
    while remaining > 0:
        step = min(SLEEP_STEP, remaining)
        sleep(step)
        remaining -= step
        if stop_path(ws).is_file():
            return True
    return stop_path(ws).is_file()


def _counts(summary: dict[str, Any]) -> dict[str, Any]:
    keys = ("sessions", "retries", "stalls")
    return {k: summary[k] for k in keys} | {"stages_passed": len(summary["stages_passed"])}


def _quote(arg: str) -> str:
    return shlex.quote(arg)
