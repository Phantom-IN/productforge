"""Observe mode (IMPLEMENTATION_PLAN.md §23): consent and the session lifecycle; summaries and
ingestion arrive in later v2 phases.

The user drives the real product in a browser ProductForge controls; ProductForge records what the
product does. Consent is asked once per workspace and recorded with a hash of the exact text the
user saw — a changed text asks again.

Sessions: ``start`` spawns the recorder (``observe/recorder.py``) with the observe venv's Python,
detached, and waits for its panel URL; ``status`` and ``stop`` talk to it only through files in
``.productforge/observe/<session>/`` (``status.json`` written by the recorder, ``stop.request``
written here). This module never imports Playwright and never opens a socket.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pflib import capabilities, config, state, workspace
from pflib.errors import CheckFailed, UsageError

CAPABILITY = "browser.observe"
PLUGIN_ROOT = Path(__file__).resolve().parents[4]
OBSERVE_STAGES = ("DISCOVERY", "PRODUCT_MODEL")
SESSION_RE = re.compile(r"^obs-\d{8}-\d{6}(?:-\d+)?$")
LIVE = ("starting", "recording", "paused", "stopping")
PROFILE_PREFIX = "pf-observe-profile-"
SCREENSHOT_MODES = ("on", "blur", "off")
START_TIMEOUT_S = 45.0
STOP_TIMEOUT_S = 20.0

CONSENT_TEXT = (
    "Observe mode opens the product in a browser window that ProductForge controls. You sign in "
    "with your own account and use the product yourself; ProductForge never clicks for you. While "
    "recording it saves, on this computer only: the pages and screens you visit, what you click "
    "(not what you type), screenshots (unless you turn them off) and the shape of the product's "
    "network traffic. Passwords, payment fields, cookies and tokens are never stored, and nothing "
    "raw is merged into the spec or committed. The product's terms of service may forbid reverse "
    "engineering or automated access — whether to use observe mode on it is your decision. You "
    "can pause or stop at any time and delete a session with `pf.py observe discard`."
)


def consent_hash(text: str | None = None) -> str:
    return hashlib.sha256((CONSENT_TEXT if text is None else text).encode("utf-8")).hexdigest()


def consent_status(st: state.WorkspaceState) -> dict[str, Any]:
    given = st.observe_consent or {}
    current = given.get("text_sha256") == consent_hash()
    return {"consented": bool(given) and current, "at": given.get("at"), "stale": bool(given)
            and not current, "text": CONSENT_TEXT}  # fmt: skip


def record_consent(ws: Path, confirmed: bool) -> dict[str, Any]:
    st = state.load(ws)
    if not confirmed:
        out = consent_status(st)
        out["message"] = (
            "nothing recorded: show the text, ask the user, then re-run with --confirmed"
        )
        return out
    now = workspace.iso(workspace.utc_now())
    st.observe_consent = {"at": now, "text_sha256": consent_hash()}
    state.save(ws, st)
    workspace.append_history(ws, {"event": "observe-consent", "text_sha256": consent_hash()})
    return consent_status(st)


def require_consent(ws: Path) -> None:
    if not consent_status(state.load(ws))["consented"]:
        raise UsageError("observe mode needs the user's consent first (pf.py observe consent)",
                         code="OBSERVE_NO_CONSENT")  # fmt: skip


# -- sessions ------------------------------------------------------------------------------------
def observe_root(ws: Path) -> Path:
    return workspace.pf_dir(ws) / workspace.OBSERVE


def recorder_python(home: Path | None = None) -> Path:
    """The observe venv's interpreter, or OBSERVE_NOT_INSTALLED."""
    cap = capabilities.load_registry().capabilities[CAPABILITY]
    prov = next(p for p in cap.providers if p.kind == "local")
    venv = capabilities.venv_path(str((prov.detect or {})["venv"]), home or Path.home())
    python = venv / "bin" / "python"
    if not (python.exists() and (venv / capabilities.VENV_READY).is_file()):
        raise UsageError(
            "observe mode is not installed: ask the user, then "
            "`pf.py deps install browser.observe --confirmed`",
            code="OBSERVE_NOT_INSTALLED",
        )
    return python


def recorder_command(python: Path, folder: Path, headless: bool = False) -> list[str]:
    cmd = [str(python), str(PLUGIN_ROOT / "observe" / "recorder.py"), "--session-dir", str(folder)]
    return cmd + (["--headless"] if headless else [])


def new_session_id(root: Path, now: datetime | None = None) -> str:
    base = "obs-" + (now or workspace.utc_now()).strftime("%Y%m%d-%H%M%S")
    sid, n = base, 1
    while (root / sid).exists():
        n += 1
        sid = f"{base}-{n}"
    return sid


def sessions(ws: Path) -> list[str]:
    root = observe_root(ws)
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and SESSION_RE.match(p.name))


def _read(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:  # reap our own exited child first, or it lingers as a zombie that os.kill still finds
        if os.waitpid(pid, os.WNOHANG)[0] == pid:
            return False
    except ChildProcessError:
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _folder(ws: Path, sid: str | None) -> Path:
    if sid is None:
        found = sessions(ws)
        if not found:
            raise UsageError("no observe session yet (pf.py observe start)",
                             code="OBSERVE_NO_SESSION")  # fmt: skip
        sid = found[-1]
    folder = observe_root(ws) / sid
    if not SESSION_RE.match(sid) or not folder.is_dir():
        raise UsageError(f"no observe session {sid!r}", code="OBSERVE_NO_SESSION")
    return folder


def session_status(ws: Path, sid: str | None = None) -> dict[str, Any]:
    folder = _folder(ws, sid)
    meta = _read(folder / "session.json")
    live = _read(folder / "status.json")
    status = str(live.get("status") or meta.get("status") or "starting")
    pid = live.get("pid") or meta.get("pid")
    alive = pid_alive(pid)
    if status in LIVE and not alive:
        status = "crashed"
    return {
        "session": folder.name,
        "status": status,
        "url": meta.get("url"),
        "started_at": meta.get("started_at"),
        "label": live.get("label"),
        "counts": live.get("counts", {}),
        "elapsed_s": live.get("elapsed_s"),
        "panel_url": live.get("panel_url") if status in ("recording", "paused") else None,
        "pid": pid,
        "folder": folder.relative_to(ws).as_posix(),
    }


def active_session(ws: Path) -> str | None:
    for sid in reversed(sessions(ws)):
        if session_status(ws, sid)["status"] in LIVE:
            return sid
    return None


def _host(url: str | None) -> str:
    return (urlsplit(url or "").hostname or "").lower()


def start(ws: Path, url: str | None = None, label: str | None = None, port: int | None = None,
          home: Path | None = None, headless: bool = False) -> dict[str, Any]:  # fmt: skip
    require_consent(ws)
    st = state.load(ws)
    if st.state.value not in OBSERVE_STAGES:
        raise UsageError(
            f"observe mode works in {' and '.join(OBSERVE_STAGES)}; the workspace is in "
            f"{st.state.value}",
            code="OBSERVE_WRONG_STAGE",
        )
    running = active_session(ws)
    if running:
        raise UsageError(f"session {running} is still recording: pf.py observe stop first",
                         code="OBSERVE_ACTIVE")  # fmt: skip
    python = recorder_python(home)
    shots = config.resolve("observe.screenshots", ws)
    if shots not in SCREENSHOT_MODES:
        raise UsageError(f"observe.screenshots must be one of {', '.join(SCREENSHOT_MODES)} "
                         f"(got {shots!r})", code="OBSERVE_BAD_CONFIG")  # fmt: skip
    pruned = prune(ws)
    target = st.product.get("target_url")
    start_url = url or target
    if not start_url or _host(start_url) == "":
        raise UsageError("observe start needs an http(s) URL (--url)", code="OBSERVE_BAD_URL")
    hosts = list(config.resolve("observe.allowed_hosts", ws)) or sorted(
        {h for h in (_host(target), _host(start_url)) if h}
    )
    cfg = {
        "port": port if port is not None else config.resolve("observe.port", ws),
        "screenshots": shots,
        "allowed_hosts": hosts,
        "max_session_minutes": config.resolve("observe.max_session_minutes", ws),
    }
    root = observe_root(ws)
    root.mkdir(parents=True, exist_ok=True)
    sid = new_session_id(root)
    folder = root / sid
    folder.mkdir()
    meta: dict[str, Any] = {
        "session": sid, "url": start_url, "label": label, "status": "starting",
        "started_at": workspace.iso(workspace.utc_now()), "config": cfg,
        "consent_sha256": st.observe_consent.get("text_sha256"),
    }  # fmt: skip
    _write(folder / "session.json", meta)
    with (folder / "recorder.log").open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            recorder_command(python, folder, headless),
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            cwd=str(folder), start_new_session=True,
        )  # fmt: skip
    meta["pid"] = proc.pid
    _write(folder / "session.json", meta)
    deadline = time.monotonic() + START_TIMEOUT_S
    while time.monotonic() < deadline:
        live = _read(folder / "status.json")
        if live.get("panel_url"):
            workspace.append_history(ws, {"event": "observe-start", "session": sid})
            return {"session": sid, "panel_url": live["panel_url"], "pid": proc.pid,
                    "pruned": pruned}  # fmt: skip
        if proc.poll() is not None or live.get("status") == "failed":
            break
        time.sleep(0.2)
    if proc.poll() is None:
        proc.kill()
        proc.wait(timeout=10)
    tail = (folder / "recorder.log").read_text(encoding="utf-8", errors="replace")[-600:]
    raise CheckFailed(f"the recorder did not start (session {sid}): {tail.strip() or 'no output'}",
                      code="OBSERVE_START_FAILED")  # fmt: skip


def _remove_profile(folder: Path) -> None:
    """Delete a crashed recorder's temporary browser profile (cookies) — ours only."""
    profile = _read(folder / "status.json").get("profile_dir")
    if not profile:
        return
    path = Path(profile)
    if path.name.startswith(PROFILE_PREFIX) and path.parent == Path(tempfile.gettempdir()):
        shutil.rmtree(path, ignore_errors=True)


def stop(ws: Path, sid: str | None = None, timeout: float = STOP_TIMEOUT_S) -> dict[str, Any]:
    info = session_status(ws, sid)
    folder = observe_root(ws) / info["session"]
    if info["status"] in LIVE:
        (folder / "stop.request").write_text(workspace.iso(workspace.utc_now()) + "\n")
        pid = info["pid"]
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and pid_alive(pid):
            time.sleep(0.2)
        for sig, wait in ((signal.SIGTERM, 5.0), (signal.SIGKILL, 2.0)):
            if not pid_alive(pid):
                break
            os.kill(pid, sig)
            end = time.monotonic() + wait
            while time.monotonic() < end and pid_alive(pid):
                time.sleep(0.1)
        workspace.append_history(ws, {"event": "observe-stop", "session": info["session"]})
    _remove_profile(folder)
    return session_status(ws, info["session"])


def discard(ws: Path, sid: str, reason: str | None) -> dict[str, Any]:
    """Delete a session's raw files (the whole folder) and log why. Live sessions stop first."""
    if not (reason or "").strip():
        raise UsageError("observe discard needs --reason", code="OBSERVE_NO_REASON")
    info = session_status(ws, sid)
    if info["status"] in LIVE:
        raise UsageError(f"session {sid} is still recording: pf.py observe stop {sid} first",
                         code="OBSERVE_ACTIVE")  # fmt: skip
    folder = observe_root(ws) / info["session"]
    _remove_profile(folder)
    files = sum(1 for p in folder.rglob("*") if p.is_file())
    shutil.rmtree(folder)
    workspace.append_history(ws, {"event": "observe-discard", "session": info["session"],
                                  "files": files, "reason": reason})  # fmt: skip
    return {"session": info["session"], "discarded": True, "files": files, "reason": reason}


def prune(ws: Path, now: datetime | None = None) -> list[str]:
    """Delete stopped sessions older than ``observe.retain_days`` (0 keeps everything)."""
    days = int(config.resolve("observe.retain_days", ws) or 0)
    if days <= 0:
        return []
    now = now or workspace.utc_now()
    pruned = []
    for sid in sessions(ws):
        info = session_status(ws, sid)
        started = info.get("started_at")
        if info["status"] in LIVE or not started:
            continue
        age = now - datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        if age.days >= days:
            discard(ws, sid, f"older than observe.retain_days ({days})")
            pruned.append(sid)
    return pruned
