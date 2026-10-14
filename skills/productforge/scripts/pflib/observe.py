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


# -- summary and ingestion ------------------------------------------------------------------------
SUMMARY = "summary.json"
ACTION_TYPES = ("click", "submit", "change")
MAX_DETAIL_WORDS = 60  # field shapes and labels only; well under any quotation concern


def _events(folder: Path) -> list[dict[str, Any]]:
    path = folder / "events.jsonl"
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if isinstance(e, dict):
            out.append(e)
    return out


def _compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(", ", ": "))


def _action_text(a: dict[str, Any]) -> str:
    name = f" “{a['name']}”" if a.get("name") else ""
    return f"{a['type']} · {a.get('role') or a.get('tag') or 'element'}{name}"


def summarise(folder: Path, prefix: str = "") -> dict[str, Any]:
    """A session folder → ``{session, screens, actions, steps, endpoints, realtime, permissions,
    errors}``: deterministic (ordered by first appearance), built only from redacted files.
    ``prefix`` is the folder's workspace-relative path, used for ``artifact`` references."""
    pre = f"{prefix.rstrip('/')}/" if prefix else ""
    events = _events(folder)
    meta = _read(folder / "session.json")
    last: dict[str, Any] = next((e for e in reversed(events) if e.get("type") == "stopped"), {})
    shots_after = {e.get("after"): e.get("file") for e in events if e.get("type") == "screenshot"}

    screens = []
    for path in sorted((folder / "screens").glob("*.json")):
        s = _read(path)
        nav = next(
            (
                e
                for e in events
                if e.get("type") == "navigate" and e.get("screen") == s.get("screen")
            ),
            {},
        )  # noqa: E501
        screens.append({
            "screen": s.get("screen"), "route": s.get("route"), "title": s.get("title", ""),
            "landmarks": s.get("landmarks", []),
            "headings": [h.get("name") for h in s.get("headings", []) if h.get("name")],
            "buttons": s.get("buttons", []),
            "inputs": [{k: i.get(k) for k in ("name", "input_type", "required")}
                       for i in s.get("inputs", [])],
            "links": [{"name": link.get("name"), "route": _route_of(link.get("href")),
                       "count": link.get("count", 1)} for link in s.get("links", [])],
            "forms": s.get("forms", 0), "tables": s.get("tables", []),
            "dialogs": s.get("dialogs", []), "tabs": s.get("tabs", []),
            "artifact": f"{pre}screens/{path.name}",
            "shot": f"{pre}{shots_after[nav['seq']]}" if nav.get("seq") in shots_after else None,
        })  # fmt: skip

    actions: dict[tuple[Any, ...], dict[str, Any]] = {}
    ordered: list[dict[str, Any]] = []
    for e in events:
        if e.get("type") not in ACTION_TYPES:
            continue
        key = (e["type"], e.get("role"), e.get("name"), e.get("route"))
        if key not in actions:
            actions[key] = {"type": e["type"], "role": e.get("role"), "name": e.get("name"),
                            "route": e.get("route"), "count": 0, "steps": [],
                            "fields": e.get("fields"), "first_seq": e.get("seq"),
                            "shot": f"{pre}{shots_after[e['seq']]}"
                            if e.get("seq") in shots_after else None}  # fmt: skip
        a = actions[key]
        a["count"] += 1
        if e.get("step") and e["step"] not in a["steps"]:
            a["steps"].append(e["step"])
        ordered.append({"seq": e.get("seq"), "action": _action_text(e), "route": e.get("route"),
                        "step": e.get("step")})  # fmt: skip

    steps: list[dict[str, Any]] = []
    for item in ordered:
        if not steps or steps[-1]["label"] != item["step"]:
            steps.append({"label": item["step"], "actions": []})
        text = f"{item['action']} on {item['route']}"
        if not steps[-1]["actions"] or steps[-1]["actions"][-1] != text:
            steps[-1]["actions"].append(text)

    endpoints: dict[tuple[str, str], dict[str, Any]] = {}
    permissions: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    last_action: dict[str, Any] | None = None
    for e in events:
        kind = e.get("type")
        if kind in ACTION_TYPES:
            last_action = e
        if kind == "request" and e.get("resource_type") != "document":
            ep_key = (str(e.get("method")), str(e.get("route")))
            fresh: dict[str, Any] = {
                "method": ep_key[0],
                "route": ep_key[1],
                "statuses": [],
                "count": 0,
                "request_shape": None,
                "response_shape": None,
                "steps": [],
                "first_seq": e.get("seq"),
            }
            ep = endpoints.setdefault(ep_key, fresh)
            ep["count"] += 1
            if e.get("status") not in ep["statuses"]:
                ep["statuses"] = sorted([*ep["statuses"], e.get("status")], key=str)
            for shape_key in ("request_shape", "response_shape"):
                if ep[shape_key] is None and e.get(shape_key) is not None:
                    ep[shape_key] = e[shape_key]
            if e.get("step") and e["step"] not in ep["steps"]:
                ep["steps"].append(e["step"])
        if kind == "request" and e.get("status") in (401, 403):
            permissions.append({"method": e.get("method"), "route": e.get("route"),
                                "status": e.get("status"), "step": e.get("step"),
                                "response_shape": e.get("response_shape"),
                                "after": _after(last_action)})  # fmt: skip
        if kind in ("console_error", "page_error"):
            text = e.get("text") or e.get("message") or ""
            found = next(
                (x for x in errors if x["text"] == text and x["route"] == e.get("route")), None
            )
            if found:
                found["count"] += 1
            else:
                errors.append({"kind": kind, "route": e.get("route"), "text": text, "count": 1})
        if kind == "request" and isinstance(e.get("status"), int) and e["status"] >= 500:
            text = f"{e.get('method')} {e.get('route')} → {e['status']}"
            errors.append({"kind": "server_error", "route": e.get("route"), "count": 1,
                           "text": text})  # fmt: skip

    realtime: dict[str, dict[str, Any]] = {}
    for e in events:
        if e.get("type") != "ws_message":
            continue
        parts = urlsplit(str(e.get("url")))
        ch = realtime.setdefault(parts.path or "/", {"channel": parts.path or "/",
                                                     "host": parts.netloc, "sent": [],
                                                     "received": []})  # fmt: skip
        bucket = ch["sent" if e.get("direction") == "sent" else "received"]
        if e.get("shape") not in bucket:
            bucket.append(e.get("shape"))

    return {
        "session": {
            "id": folder.name,
            "url": meta.get("url"),
            "started_at": meta.get("started_at"),
            "ended": last.get("reason"),
            "events": len(events),
        },  # fmt: skip
        "screens": screens,
        "actions": sorted(actions.values(), key=lambda a: a["first_seq"] or 0),
        "steps": steps,
        "endpoints": sorted(endpoints.values(), key=lambda x: x["first_seq"] or 0),
        "realtime": list(realtime.values()),
        "permissions": permissions,
        "errors": errors,
    }


def _after(action: dict[str, Any] | None) -> str | None:
    return f"{_action_text(action)} on {action.get('route')}" if action else None


def _field_text(f: dict[str, Any]) -> str:
    required = ", required" if f.get("required") else ""
    return f"{f.get('name') or '(unnamed)'} ({f.get('input_type')}{required})"


def _link_text(link: dict[str, Any]) -> str:
    times = f" ×{link['count']}" if link.get("count", 1) > 1 else ""
    return f"{link.get('name')}{times} → `{link.get('route')}`"


def _route_of(href: Any) -> str | None:
    return (urlsplit(href).path or "/") if isinstance(href, str) and href else None


def _words(text: str, limit: int = MAX_DETAIL_WORDS) -> str:
    words = text.split()
    return text if len(words) <= limit else " ".join(words[:limit]) + " …"


def observation_records(summary: dict[str, Any], prefix: str) -> list[str]:
    """OB record blocks (provisional IDs ``OB-?n``, Evidence ``S-?1``) for a summary."""
    pre = f"{prefix.rstrip('/')}/"
    out: list[tuple[str, str, str, str, str | None]] = []  # title, kind, detail, artifact, step
    for s in summary["screens"]:
        bits = [f"Route `{s['route']}` titled “{s['title']}”."]
        for label, values in (("Landmarks", s["landmarks"]), ("Headings", s["headings"]),
                              ("Buttons", s["buttons"]), ("Tabs", s["tabs"]),
                              ("Dialogs", s["dialogs"])):  # fmt: skip
            if values:
                bits.append(f"{label}: {'; '.join(values)}.")
        if s["inputs"]:
            fields = [_field_text(i) for i in s["inputs"]]
            bits.append(f"Inputs: {'; '.join(fields)}.")
        if s["forms"]:
            bits.append(f"Forms: {s['forms']}.")
        for t in s["tables"]:
            bits.append(f"Table with columns {', '.join(t.get('headers') or ['?'])} "
                        f"({t.get('rows', 0)} rows).")  # fmt: skip
        if s["links"]:
            links = [_link_text(x) for x in s["links"]]
            bits.append(f"Links: {'; '.join(links)}.")
        out.append((f"Screen `{s['route']}`", "screen", " ".join(bits), s["artifact"], None))
    for a in summary["actions"]:
        detail = f"{_action_text(a)} on `{a['route']}`"
        if a.get("fields"):
            names = [_field_text(f) for f in a["fields"]]
            detail += f" with fields {', '.join(names)}"
        detail += f" (×{a['count']})."
        title = f"{a['type'].capitalize()} {a.get('role') or 'element'} “{a.get('name') or '?'}” on `{a['route']}`"  # noqa: E501
        out.append((title, "action", detail, a["shot"] or "", "; ".join(a["steps"]) or None))
    for ep in summary["endpoints"]:
        statuses = ", ".join(str(s) for s in ep["statuses"])
        detail = f"`{ep['method']} {ep['route']}` → {statuses} (×{ep['count']})."
        if ep["request_shape"] is not None:
            detail += f" Request `{_compact(ep['request_shape'])}`."
        if ep["response_shape"] is not None:
            detail += f" Response `{_compact(ep['response_shape'])}`."
        out.append((f"Endpoint `{ep['method']} {ep['route']}`", "endpoint", detail,
                    f"{pre}network.har", "; ".join(ep["steps"]) or None))  # fmt: skip
    for ch in summary["realtime"]:
        detail = f"WebSocket `{ch['channel']}`."
        if ch["sent"]:
            detail += f" Sent {'; '.join(f'`{_compact(x)}`' for x in ch['sent'])}."
        if ch["received"]:
            detail += f" Received {'; '.join(f'`{_compact(x)}`' for x in ch['received'])}."
        out.append((f"Realtime `{ch['channel']}`", "realtime", detail, f"{pre}events.jsonl", None))
    for p in summary["permissions"]:
        detail = f"`{p['method']} {p['route']}` → {p['status']}"
        detail += f" after {p['after']}." if p["after"] else "."
        if p["response_shape"] is not None:
            detail += f" Response `{_compact(p['response_shape'])}`."
        out.append((f"Permission `{p['method']} {p['route']}` → {p['status']}", "permission",
                    detail, f"{pre}network.har", p["step"]))  # fmt: skip
    for err in summary["errors"]:
        detail = (
            f"{err['kind'].replace('_', ' ')} on `{err['route']}` (×{err['count']}): {err['text']}"
        )
        title = f"Error on `{err['route']}`: {' '.join(err['text'].split()[:8])}"
        out.append((title, "error", detail, f"{pre}events.jsonl", None))
    blocks = []
    for n, (title, kind, detail, artifact, step) in enumerate(out, 1):
        lines = [
            f"### OB-?{n} — {title}",
            f"- Kind: {kind}",
            f"- Detail: {_words(detail)}",
            "- Evidence: S-?1",
            f"- Artifact: {artifact}",
            "- Confidence: CONFIRMED",
        ]
        if step:
            lines.append(f"- Step: {step}")
        blocks.append("\n".join(lines) + "\n")
    return blocks


def source_record(summary: dict[str, Any], st: state.WorkspaceState) -> str:
    from pflib import urls

    sid = summary["session"]["id"]
    start = summary["session"]["url"] or st.product.get("target_url") or ""
    parts = urlsplit(start)
    url = f"{parts.scheme}://{parts.netloc}/?pf_observe={sid}"
    day = str(summary["session"]["started_at"] or workspace.iso(workspace.utc_now()))[:10]
    counts = (f"{len(summary['screens'])} screens, {len(summary['endpoints'])} endpoints, "
              f"{len(summary['realtime'])} realtime channels")  # fmt: skip
    return "\n".join([
        f"### S-?1 — Observed session {sid}",
        f"- URL: {url}",
        f"- Canonical URL: {urls.canonicalize(url)}",
        "- Category: observed-session",
        "- Tier: 1",
        "- Authority: High",
        f"- Relevant area: {st.scope.get('text') or 'observed product behaviour'}",
        f"- Published: {day}",
        f"- Last inspected: {day}",
        f"- Notes: Recorded in observe mode with the user's own account ({counts}); redacted on "
        "write; raw files stay on this computer.",
    ]) + "\n"  # fmt: skip


def ingest(ws: Path, sid: str) -> dict[str, Any]:
    """Summarise a stopped session, stage one S + its OB records, and merge them."""
    from pflib import merge

    info = session_status(ws, sid)
    if info["status"] in LIVE:
        raise UsageError(f"session {sid} is still recording: pf.py observe stop {sid} first",
                         code="OBSERVE_ACTIVE")  # fmt: skip
    folder = observe_root(ws) / info["session"]
    prefix = folder.relative_to(ws).as_posix()
    summary = summarise(folder, prefix)
    _write(folder / SUMMARY, summary)
    st = state.load(ws)
    blocks = observation_records(summary, prefix)
    run_id, run_dir = workspace.create_staging_run(ws, "observe")
    (run_dir / "research").mkdir(parents=True, exist_ok=True)
    (run_dir / "research" / "sources.md").write_text(source_record(summary, st), encoding="utf-8")
    (run_dir / "research" / "observations.md").write_text("\n".join(blocks), encoding="utf-8")
    report = merge.merge(ws, run_id)
    source = report.id_map.get("S-?1") or next(
        (v for k, v in report.id_map.items() if k.startswith("S-")), None
    )
    workspace.append_history(ws, {"event": "observe-ingest", "session": info["session"],
                                  "run_id": run_id, "observations": len(blocks)})  # fmt: skip
    return {"source": source, "observations": len(blocks), "merged": run_id,
            "new_ids": report.new_ids, "summary": f"{prefix}/{SUMMARY}"}  # fmt: skip
