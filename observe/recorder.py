"""Observe-mode recorder (IMPLEMENTATION_PLAN.md §23) — runs with the observe venv's Python.

``pf.py observe start`` launches ``<venv>/bin/python observe/recorder.py --session-dir <dir>``.
The recorder opens a real, visible Chromium window at the product URL plus the control panel
(``server.py``) and records what the product does while the **user** drives it. It never clicks,
types or answers a dialog for the user.

Everything written goes through ``redact`` first. The browser profile (cookies, local storage)
lives in a temporary folder that is deleted when the session ends, so no cookie or token is ever
kept. Session folder::

    session.json    written by pf.py (URL, config); read here
    status.json     live state for pf.py and the panel (atomic writes)
    events.jsonl    navigations, clicks, submits, requests, realtime messages, errors, dialogs
    screens/NNN.json  one accessibility snapshot (roles + accessible names) per screen
    shots/NNNN.png  screenshots per step (``observe.screenshots``: on · blur · off)
    network.har     requests with allowlisted headers and body *shapes* only
    stop.request    created by ``pf.py observe stop``

The ``Recorder`` class attaches to any Playwright ``BrowserContext``; ``main()`` is the only
place a browser is launched.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import signal
import sys
import tempfile
import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import redact  # noqa: E402
from server import PanelServer  # noqa: E402

ASSET_TYPES = frozenset({"image", "stylesheet", "font", "media", "script", "manifest",
                         "texttrack", "ping"})  # fmt: skip
MAX_BODY_BYTES = 2_000_000
SHOT_DELAY_S = 0.7  # let the page react to a click before the screenshot
SHOT_GAP_S = 1.0  # at most one screenshot per second
BODY_GRACE_S = 1.5  # how long a JSON response waits for its paused body read
STATUS_EVERY_S = 1.0
HAR_EVERY_S = 15.0
COUNTS = ("events", "screens", "requests", "ws_frames", "shots", "dropped", "assets")
# observe.screenshots = "blur": text and images smudged, layout, colours and shapes kept. Applied
# by Playwright for the duration of the screenshot only.
BLUR_CSS = (
    "*, *::before, *::after, ::placeholder { color: transparent !important;"
    " -webkit-text-fill-color: transparent !important; caret-color: transparent !important;"
    " text-shadow: 0 0 9px rgba(128, 128, 128, 0.95) !important; }"
    " img, video, canvas, picture, svg image { filter: blur(12px) !important; }"
)
# Always masked in screenshots: secrets, payment fields, and every iframe (payment and sign-in
# widgets live in third-party frames).
PRIVATE_SELECTOR = (
    "input[type=password], input[autocomplete^='cc-'], input[name*='card' i],"
    " input[name*='cvc' i], input[name*='cvv' i], iframe, [data-pf-private]"
)

# Injected into every document: reports clicks, submits and field changes with the target's role,
# accessible name and a selector. It never reads `.value`, so typed text and passwords stay unseen.
CAPTURE_JS = r"""
(() => {
  if (window.__pfCapture) return;
  window.__pfCapture = true;
  const clean = (s) => (s || "").replace(/\s+/g, " ").trim().slice(0, 80);
  const TAG_ROLE = {A: "link", BUTTON: "button", SELECT: "combobox", TEXTAREA: "textbox",
                    SUMMARY: "button", OPTION: "option", IMG: "img"};
  const INPUT_ROLE = {checkbox: "checkbox", radio: "radio", submit: "button", button: "button",
                      reset: "button", range: "slider", search: "searchbox", image: "button"};
  const FIELD = ["INPUT", "SELECT", "TEXTAREA"];
  const roleOf = (el) => el.getAttribute("role")
    || (el.tagName === "INPUT" ? (INPUT_ROLE[el.type] || "textbox") : TAG_ROLE[el.tagName])
    || el.tagName.toLowerCase();
  const nameOf = (el) => {
    const by = (el.getAttribute("aria-labelledby") || "").split(/\s+/).filter(Boolean)
      .map((id) => (document.getElementById(id) || {}).innerText || "").join(" ");
    const label = el.labels && el.labels.length ? el.labels[0].innerText : "";
    return clean(el.getAttribute("aria-label") || by || label || el.getAttribute("title")
      || el.getAttribute("alt") || el.getAttribute("placeholder")
      || (FIELD.includes(el.tagName) || el.tagName === "FORM"
          ? (el.getAttribute("name") || el.id || "") : el.innerText));
  };
  const selectorOf = (el) => {
    const parts = [];
    for (let n = el; n && n.nodeType === 1 && parts.length < 4; n = n.parentElement) {
      let p = n.tagName.toLowerCase();
      const tid = n.getAttribute("data-testid") || n.getAttribute("data-test");
      if (tid) { parts.unshift(`${p}[data-testid="${tid}"]`); break; }
      if (n.id && !/\d{3,}/.test(n.id)) { parts.unshift(`${p}#${n.id}`); break; }
      const cls = [...n.classList].filter((c) => !/\d{3,}|^css-|^sc-/.test(c)).slice(0, 2);
      if (cls.length) p += "." + cls.join(".");
      parts.unshift(p);
    }
    return parts.join(" > ").slice(0, 200);
  };
  const ACTIONABLE = "a,button,input,select,textarea,summary,label,[role=button],[role=link]," +
    "[role=menuitem],[role=tab],[role=checkbox],[role=switch],[role=option],[onclick]";
  // Names of repeated items (rows, list entries, cards) are user data: the recorder masks them.
  const ITEM = "li,tr,[role=row],[role=listitem],[role=gridcell],[role=option],article";
  const NAV = "nav,[role=navigation],[role=tablist],[role=toolbar],[role=menubar]";
  const describe = (el) => ({role: roleOf(el), name: nameOf(el), selector: selectorOf(el),
    tag: el.tagName.toLowerCase(), input_type: el.tagName === "INPUT" ? el.type : null,
    in_item: !!el.closest(ITEM), in_nav: !!el.closest(NAV)});
  const send = (e) => { try { window.__pfRecord(e); } catch (_) { /* recorder gone */ } };
  document.addEventListener("click", (ev) => {
    const el = ev.target.closest ? (ev.target.closest(ACTIONABLE) || ev.target) : null;
    if (el) send({type: "click", ...describe(el)});
  }, true);
  document.addEventListener("submit", (ev) => {
    const form = ev.target;
    const fields = [...form.elements]
      .filter((f) => FIELD.includes(f.tagName) && !["hidden", "submit", "button"].includes(f.type))
      .slice(0, 40)
      .map((f) => ({role: roleOf(f), name: nameOf(f), input_type: f.type || f.tagName.toLowerCase(),
                   required: !!f.required}));
    send({type: "submit", ...describe(form), fields});
  }, true);
  document.addEventListener("change", (ev) => {
    const el = ev.target;
    if (el && FIELD.includes(el.tagName)) send({type: "change", ...describe(el)});
  }, true);
})();
"""

# One screen's accessibility inventory: roles, accessible names, counts. Never field values or
# table cell text.
INVENTORY_JS = r"""
() => {
  const clean = (s) => (s || "").replace(/\s+/g, " ").trim().slice(0, 80);
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const all = (sel) => [...document.querySelectorAll(sel)].filter(visible);
  const uniq = (xs, max) => [...new Set(xs.filter(Boolean))].slice(0, max);
  const FIELD = ["INPUT", "SELECT", "TEXTAREA"];
  const nameOf = (el) => clean(el.getAttribute("aria-label")
    || (el.labels && el.labels.length ? el.labels[0].innerText : "")
    || el.getAttribute("title") || el.getAttribute("alt") || el.getAttribute("placeholder")
    || (FIELD.includes(el.tagName) ? (el.getAttribute("name") || "") : el.innerText));
  const ITEM = "li,tr,[role=row],[role=listitem],[role=gridcell],[role=option],article";
  const NAV = "nav,[role=navigation],[role=tablist],[role=toolbar],[role=menubar]";
  const where = (el) => ({in_item: !!el.closest(ITEM), in_nav: !!el.closest(NAV)});
  const LANDMARK = {HEADER: "banner", NAV: "navigation", MAIN: "main", ASIDE: "complementary",
                    FOOTER: "contentinfo"};
  const buttons = all("button,[role=button],input[type=submit],input[type=button]");
  const links = all("a[href],[role=link]");
  const inputs = all("input:not([type=hidden]),select,textarea,[role=textbox],[role=combobox]," +
                     "[role=checkbox],[role=switch]");
  return {
    title: clean(document.title),
    landmarks: uniq(all("header,nav,main,aside,footer,[role=banner],[role=navigation]," +
      "[role=main]," +
      "[role=complementary],[role=contentinfo],[role=search]")
      .map((el) => el.getAttribute("role") || LANDMARK[el.tagName]), 20),
    headings: all("h1,h2,h3,[role=heading]").slice(0, 40).map((el) => ({
      level: Number(el.getAttribute("aria-level") || el.tagName.slice(1)) || 2,
      name: clean(el.innerText), ...where(el)})),
    buttons: uniq(buttons.map(nameOf), 60),
    links: links.slice(0, 60).map((el) => ({name: nameOf(el), href: el.href || null,
                                            ...where(el)})),
    inputs: inputs.slice(0, 60).map((el) => ({
      role: el.getAttribute("role") || ({checkbox: "checkbox", radio: "radio", search: "searchbox",
        range: "slider"}[el.type] || (el.tagName === "SELECT" ? "combobox" : "textbox")),
      input_type: el.tagName === "INPUT" ? el.type : el.tagName.toLowerCase(),
      name: nameOf(el), required: !!el.required})),
    forms: all("form").length,
    tables: all("table,[role=table],[role=grid]").slice(0, 10).map((el) => ({
      headers: uniq([...el.querySelectorAll("th,[role=columnheader]")]
        .map((h) => clean(h.innerText)), 30),
      rows: el.querySelectorAll("tbody tr,[role=row]").length})),
    lists: all("ul,ol,[role=list]").filter((el) => el.children.length >= 3).length,
    dialogs: uniq(all("dialog[open],[role=dialog],[role=alertdialog]").map(nameOf), 10),
    tabs: uniq(all("[role=tab]").map(nameOf), 30),
    counts: {buttons: buttons.length, links: links.length, inputs: inputs.length},
  };
}
"""


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, data: Any) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def log(message: str) -> None:
    print(f"{now_iso()} {redact.text(message)}", file=sys.stderr, flush=True)


class Recorder:
    """Records one session from a BrowserContext into ``folder`` (see the module docstring)."""

    def __init__(
        self, context: Any, folder: Path, config: dict[str, Any], session: str = ""
    ) -> None:
        self.context = context
        self.folder = folder
        self.session = session or folder.name
        (folder / "screens").mkdir(parents=True, exist_ok=True)
        (folder / "shots").mkdir(exist_ok=True)
        self._events = (folder / "events.jsonl").open("a", encoding="utf-8")
        self.allowed = {h.lower().strip(".") for h in config.get("allowed_hosts") or []}
        self.screenshots = config.get("screenshots", "on")
        self.ignore_origins: set[str] = set()
        self.panel_url: str | None = None
        self.profile_dir: str | None = None
        self.state = "recording"
        self.label: str | None = None
        self.started = time.monotonic()
        self.started_at = now_iso()
        self.counts = dict.fromkeys(COUNTS, 0)
        self.seq = 0
        self.pending: deque[tuple[str, Any, Any]] = deque()
        self.commands: deque[tuple[str, str | None]] = deque()  # appended by the panel thread
        self.shots_due: list[tuple[float, Any, int]] = []
        self.screens: dict[str, int] = {}
        self.ws_shapes: set[str] = set()
        self.har: list[dict[str, Any]] = []
        self.bodies: dict[tuple[str, str], deque[bytes]] = {}  # (method, url) → captured bodies
        self.capturing: dict[tuple[str, str], int] = {}  # body reads in flight
        self.cdp_bodies = False  # True once a page's response-stage capture is enabled
        self._attached: dict[int, str] = {}  # id(page) → "attaching" | "ready"
        self.deferred: list[tuple[str, Any, Any]] = []  # responses whose body is still in flight
        self.stop_requested: str | None = None
        self._last_shot = 0.0
        self._last_status = 0.0
        self._last_har = time.monotonic()
        context.expose_binding("__pfRecord", self._on_dom)
        context.add_init_script(CAPTURE_JS)
        context.on("page", self.attach)
        for page in context.pages:
            self.attach(page)
            try:
                page.evaluate(CAPTURE_JS)
            except Exception as exc:  # a page still loading gets the init script instead
                log(f"capture script: {type(exc).__name__}")

    # -- what the panel sees ------------------------------------------------------------------
    def status(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "status": self.state,
            "paused": self.state == "paused",
            "label": self.label,
            "counts": dict(self.counts),
            "elapsed_s": round(time.monotonic() - self.started, 1),
            "started_at": self.started_at,
            "panel_url": self.panel_url,
            "pid": os.getpid(),
            "profile_dir": self.profile_dir,
        }

    def command(self, name: str, arg: str | None = None) -> None:
        self.commands.append((name, arg))

    # -- listeners (run while Playwright waits; they only queue) -------------------------------
    def open(self, url: str, timeout_ms: int = 60_000) -> Any:
        """A new tab at ``url`` — capture is fully attached *before* the first navigation (a
        document that starts loading before ``Fetch.enable`` lands is never intercepted)."""
        page = self.context.new_page()
        self.attach(page)
        deadline = time.monotonic() + 5
        while self._attached.get(id(page)) != "ready" and time.monotonic() < deadline:
            page.wait_for_timeout(20)  # the page event's handler is mid-attach: let it finish
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        return page

    def attach(self, page: Any) -> None:
        if id(page) in self._attached:  # the page event and open() both get here
            return
        self._attached[id(page)] = "attaching"
        page.on("framenavigated", lambda f: self._queue("nav", page, f, f == page.main_frame))
        page.on("response", lambda r: self._queue("response", page, (r, time.monotonic())))
        page.on("websocket", lambda ws: self._on_ws(page, ws))
        page.on("console", lambda m: self._queue("console", page, m, m.type == "error"))
        page.on("pageerror", lambda err: self._queue("pageerror", page, err))
        # A dialog listener that only records: the user answers the dialog in the window.
        page.on("dialog", lambda d: self._queue("dialog", page, d))
        self._capture_bodies(page)
        self._attached[id(page)] = "ready"

    def _capture_bodies(self, page: Any) -> None:
        """Read JSON API bodies while the response is paused (CDP Fetch, response stage).

        A body read after the ``response`` event is lost when the page navigates first (a
        sign-in fetch followed by a redirect). Pausing at the response stage reads it before the
        page sees it; the original response then continues untouched — never re-fetched, never
        modified.
        """
        try:
            cdp = self.context.new_cdp_session(page)
        except Exception as exc:  # not Chromium: fall back to reading bodies late
            log(f"cdp session: {type(exc).__name__}")
            return

        def paused(ev: dict[str, Any]) -> None:
            request = ev.get("request", {})
            key = (request.get("method", "GET"), request.get("url", ""))
            try:
                status = ev.get("responseStatusCode") or 0
                headers = {h["name"].lower(): h["value"] for h in ev.get("responseHeaders") or []}
                size = int(headers.get("content-length") or 0)
                is_json = "json" in headers.get("content-type", "")
                if (self.state == "recording" and self.allowed_url(key[1]) and 200 <= status < 300
                        and is_json and size <= MAX_BODY_BYTES):  # fmt: skip
                    self.capturing[key] = self.capturing.get(key, 0) + 1
                    got = cdp.send("Fetch.getResponseBody", {"requestId": ev["requestId"]})
                    raw = got.get("body", "")
                    data = base64.b64decode(raw) if got.get("base64Encoded") else raw.encode()
                    queue = self.bodies.setdefault(key, deque())
                    queue.append(data[:MAX_BODY_BYTES])
                    while len(queue) > 20:  # bounded: bodies nobody asked for are dropped
                        queue.popleft()
            except Exception as exc:
                log(f"body capture: {type(exc).__name__}: {exc}")
            finally:
                if self.capturing.get(key):
                    self.capturing[key] -= 1
                try:
                    cdp.send("Fetch.continueRequest", {"requestId": ev["requestId"]})
                except Exception as exc:
                    log(f"continue: {type(exc).__name__}")

        cdp.on("Fetch.requestPaused", paused)
        patterns = [{"urlPattern": "*", "resourceType": kind, "requestStage": "Response"}
                    for kind in ("XHR", "Fetch")]  # fmt: skip
        try:
            cdp.send("Fetch.enable", {"patterns": patterns})
            self.cdp_bodies = True
        except Exception as exc:
            log(f"fetch enable: {type(exc).__name__}")

    def _queue(self, kind: str, page: Any, obj: Any, wanted: bool = True) -> None:
        if wanted and self.state == "recording":
            self.pending.append((kind, page, obj))

    def _on_dom(self, source: dict[str, Any], payload: Any) -> None:
        frame_url = getattr(source.get("frame"), "url", "") or ""
        if isinstance(payload, dict) and self.allowed_url(frame_url):
            # the route where the user acted, before any navigation it causes
            self._queue("dom", source.get("page"), {**payload, "route": redact.route(frame_url)})

    def _on_ws(self, page: Any, ws: Any) -> None:
        if not self.allowed_url(ws.url):
            self.counts["dropped"] += 1
            return
        self._queue("ws_open", page, ws.url)
        ws.on("framesent", lambda p: self._queue("ws_frame", page, (ws.url, "sent", p)))
        ws.on("framereceived", lambda p: self._queue("ws_frame", page, (ws.url, "received", p)))
        ws.on("close", lambda _ws: self._queue("ws_close", page, ws.url))

    def allowed_url(self, url: str) -> bool:
        parts = urlsplit(url)
        if f"{parts.scheme}://{parts.netloc}" in self.ignore_origins:
            return False
        host = (parts.hostname or "").lower()
        return bool(host) and any(host == h or host.endswith("." + h) for h in self.allowed)

    # -- the main loop's work ------------------------------------------------------------------
    def pump(self, limit: int = 300) -> None:
        self._apply_commands()
        done = 0
        while self.pending and done < limit:
            kind, page, obj = self.pending.popleft()
            done += 1
            try:
                getattr(self, f"_do_{kind}")(page, obj)
            except Exception as exc:  # a closed page or evicted body never ends the session
                log(f"{kind}: {type(exc).__name__}: {exc}")
        self.pending.extend(self.deferred)
        self.deferred.clear()
        self._take_due_shots()
        self.write_status()
        if time.monotonic() - self._last_har > HAR_EVERY_S:
            self.write_har()

    def write_event(self, e: dict[str, Any]) -> dict[str, Any]:
        self.seq += 1
        rec = {"seq": self.seq, "t": now_iso(), **redact.event(e)}
        if self.label and "step" not in rec:
            rec["step"] = self.label
        self._events.write(json.dumps(rec, sort_keys=True) + "\n")
        self._events.flush()
        self.counts["events"] += 1
        return rec

    def write_status(self, force: bool = False) -> None:
        if force or time.monotonic() - self._last_status >= STATUS_EVERY_S:
            write_json(self.folder / "status.json", self.status())
            self._last_status = time.monotonic()

    def _apply_commands(self) -> None:
        while self.commands:
            name, arg = self.commands.popleft()
            if name == "pause" and self.state == "recording":
                self.state = "paused"
                self.pending.clear()
                self.shots_due.clear()
                self.write_event({"type": "paused"})
            elif name == "resume" and self.state == "paused":
                self.state = "recording"
                self.write_event({"type": "resumed"})
            elif name == "label":
                self.label = redact.label(arg) or None
                self.write_event({"type": "label", "label": self.label or ""})
            elif name == "stop":
                self.stop_requested = "stopped from the panel"
            self.write_status(force=True)

    def _route(self, page: Any) -> str:
        try:
            return redact.route(page.url)
        except Exception:
            return "?"

    def _do_nav(self, page: Any, frame: Any) -> None:
        url = frame.url
        if not self.allowed_url(url):
            if not url.startswith(("about:", "chrome:", "data:")) and not self._ignored(url):
                self.counts["dropped"] += 1
            return
        route = redact.route(url)
        e: dict[str, Any] = {"type": "navigate", "url": url, "route": route}
        if route not in self.screens:
            try:
                page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception as exc:
                log(f"load state: {type(exc).__name__}")
            n = len(self.screens) + 1
            self.screens[route] = n
            inventory = page.evaluate(INVENTORY_JS)
            screen = redact.event({"screen": n, "route": route, "url": url, **inventory})
            for key in ("links", "headings"):  # masked repeated items → one entry with a count
                screen[key] = redact.collapse(screen.get(key) or [])
            write_json(self.folder / "screens" / f"{n:03d}.json", screen)
            self.counts["screens"] += 1
            e.update(screen=n, title=inventory.get("title", ""))
        rec = self.write_event(e)
        self._want_shot(page, rec["seq"])

    def _ignored(self, url: str) -> bool:
        parts = urlsplit(url)
        return f"{parts.scheme}://{parts.netloc}" in self.ignore_origins

    def _do_dom(self, page: Any, payload: dict[str, Any]) -> None:
        kind = payload.get("type")
        if kind not in ("click", "submit", "change"):
            return
        keep = ("role", "name", "selector", "tag", "input_type", "fields", "in_item", "in_nav")
        e = {
            "type": kind,
            "route": payload.get("route") or self._route(page),
            **{k: payload.get(k) for k in keep},
        }
        rec = self.write_event({k: v for k, v in e.items() if v is not None})
        if kind in ("click", "submit"):
            self._want_shot(page, rec["seq"])

    def _do_response(self, page: Any, item: tuple[Any, float]) -> None:
        response, seen = item
        request = response.request
        url = response.url
        if not self.allowed_url(url):
            if not self._ignored(url) and not url.startswith("data:"):
                self.counts["dropped"] += 1
            return
        rtype = request.resource_type
        if rtype in ASSET_TYPES:
            self.counts["assets"] += 1
            return
        req_ct = request.headers.get("content-type")
        res_ct = response.headers.get("content-type", "")
        try:
            post = request.post_data_buffer
        except Exception:
            post = None
        req_shape = redact.body(req_ct, post)
        res_shape = None
        if "json" in res_ct and rtype != "document":
            key = (request.method, url)
            captured = self.bodies.get(key)
            waited = time.monotonic() - seen
            if not captured and self.cdp_bodies and (waited < BODY_GRACE_S or (
                    self.capturing.get(key) and waited < 5 * BODY_GRACE_S)):  # fmt: skip
                # the response event and the paused read come on different CDP sessions, in
                # either order: wait a moment for the read before falling back
                self.deferred.append(("response", page, item))
                return
            body = captured.popleft() if captured else self._late_body(response)
            res_shape = redact.body(res_ct, body) if body is not None else {"kind": "unavailable"}
        e = {"type": "request", "method": request.method, "url": url, "route": redact.route(url),
             "status": response.status, "resource_type": rtype,
             "content_type": res_ct.split(";")[0].strip() or None,
             "request_shape": req_shape, "response_shape": res_shape}  # fmt: skip
        self.write_event({k: v for k, v in e.items() if v is not None})
        self.counts["requests"] += 1
        self.har.append(self._har_entry(request, response, req_ct, res_ct, req_shape, res_shape))

    def _late_body(self, response: Any) -> bytes | None:
        """Without a captured body (no CDP, or capture failed): read it now if it is still there."""
        try:
            data: bytes = response.body()
        except Exception as exc:
            log(f"response body: {type(exc).__name__}")
            return None
        return data if len(data) <= MAX_BODY_BYTES else None

    def _do_ws_open(self, page: Any, url: str) -> None:
        self.write_event({"type": "ws_open", "url": url, "route": self._route(page)})

    def _do_ws_close(self, page: Any, url: str) -> None:
        self.write_event({"type": "ws_close", "url": url})

    def _do_ws_frame(self, page: Any, item: tuple[str, str, str | bytes]) -> None:
        url, direction, payload = item
        self.counts["ws_frames"] += 1
        if isinstance(payload, bytes):
            shape: Any = {"kind": "binary", "bytes": redact.size_bucket(len(payload))}
        else:
            shape = redact.body(None, payload)
        key = json.dumps([redact.url(url), direction, shape], sort_keys=True)
        if key not in self.ws_shapes:  # one event per distinct message shape
            self.ws_shapes.add(key)
            self.write_event({"type": "ws_message", "url": url, "direction": direction,
                              "shape": shape})  # fmt: skip

    def _do_console(self, page: Any, msg: Any) -> None:
        if self.allowed_url(page.url):
            self.write_event(
                {"type": "console_error", "text": msg.text, "route": self._route(page)}
            )

    def _do_pageerror(self, page: Any, err: Any) -> None:
        if self.allowed_url(page.url):
            self.write_event(
                {"type": "page_error", "message": str(err), "route": self._route(page)}
            )

    def _do_dialog(self, page: Any, dialog: Any) -> None:
        if self.allowed_url(page.url):
            self.write_event({"type": "dialog", "kind": dialog.type, "message": dialog.message,
                              "route": self._route(page)})  # fmt: skip

    # -- screenshots -----------------------------------------------------------------------------
    def _want_shot(self, page: Any, seq: int) -> None:
        if self.screenshots != "off" and page is not None:
            self.shots_due.append((time.monotonic() + SHOT_DELAY_S, page, seq))

    def _take_due_shots(self) -> None:
        now = time.monotonic()
        due = [s for s in self.shots_due if s[0] <= now]
        if not due or now - self._last_shot < SHOT_GAP_S:
            return
        self.shots_due = [s for s in self.shots_due if s[0] > now]
        _, page, seq = due[-1]  # the latest due step wins; earlier ones in the same second merge
        if page.is_closed() or not self.allowed_url(page.url):
            return
        n = self.counts["shots"] + 1
        rel = f"shots/{n:04d}.png"
        try:
            page.screenshot(
                path=str(self.folder / rel),
                mask=[page.locator(PRIVATE_SELECTOR)],
                style=BLUR_CSS if self.screenshots == "blur" else None,
                caret="hide",
                timeout=5000,
            )
        except Exception as exc:
            log(f"screenshot: {type(exc).__name__}")
            return
        self._last_shot = time.monotonic()
        self.counts["shots"] += 1
        self.write_event({"type": "screenshot", "file": rel, "after": seq,
                          "route": self._route(page)})  # fmt: skip

    # -- HAR -------------------------------------------------------------------------------------
    def _har_entry(self, request: Any, response: Any, req_ct: str | None, res_ct: str,
                   req_shape: Any, res_shape: Any) -> dict[str, Any]:  # fmt: skip
        safe_url = redact.url(request.url)

        def pairs(h: dict[str, str]) -> list[dict[str, str]]:
            return [{"name": k, "value": v} for k, v in sorted(redact.headers(h).items())]

        req: dict[str, Any] = {
            "method": request.method, "url": safe_url, "httpVersion": "HTTP/1.1", "cookies": [],
            "headers": pairs(request.headers),
            "queryString": [{"name": k, "value": v}
                            for k, v in parse_qsl(urlsplit(safe_url).query, True)],
            "headersSize": -1, "bodySize": -1,
        }  # fmt: skip
        if req_shape is not None:
            req["postData"] = {"mimeType": (req_ct or "").split(";")[0],
                               "text": json.dumps(req_shape, sort_keys=True)}  # fmt: skip
        return {
            "startedDateTime": now_iso(), "time": 0, "request": req,
            "response": {
                "status": response.status, "statusText": response.status_text,
                "httpVersion": "HTTP/1.1", "cookies": [], "headers": pairs(response.headers),
                "content": {"size": -1, "mimeType": res_ct.split(";")[0],
                            "text": json.dumps(res_shape, sort_keys=True) if res_shape else "",
                            "comment": "field shape only; values are never stored"},
                "redirectURL": "", "headersSize": -1, "bodySize": -1,
            },
            "cache": {}, "timings": {"send": 0, "wait": 0, "receive": 0},
            "_resourceType": request.resource_type,
        }  # fmt: skip

    def write_har(self) -> None:
        creator = {"name": "ProductForge observe", "version": "1"}
        har = {"log": {"version": "1.2", "creator": creator,
                       "pages": [], "entries": self.har}}  # fmt: skip
        write_json(self.folder / "network.har", har)
        self._last_har = time.monotonic()

    # -- lifecycle -------------------------------------------------------------------------------
    def _yield(self) -> None:
        """Let Playwright deliver pending events (it only does so while a call waits)."""
        pages = [p for p in self.context.pages if not p.is_closed()]
        try:
            if pages:
                pages[0].wait_for_timeout(50)
        except Exception as exc:
            log(f"yield: {type(exc).__name__}")

    def run(self, max_seconds: float) -> str:
        """Pump until the panel, ``pf.py observe stop``, the time limit or the window ends it."""
        stop_file = self.folder / "stop.request"
        while True:
            if self.stop_requested:
                return self.stop_requested
            if stop_file.exists():
                return "stopped by pf.py observe stop"
            if time.monotonic() - self.started > max_seconds:
                return "time limit reached (observe.max_session_minutes)"
            pages = [p for p in self.context.pages if not p.is_closed()]
            if not pages:
                return "browser window closed"
            try:
                pages[0].wait_for_timeout(200)  # Playwright delivers events while it waits
            except Exception:
                return "browser window closed"
            self.pump()

    def stop(self, reason: str) -> None:
        self.state = "stopping"
        self.write_status(force=True)
        self._apply_commands()
        for _ in range(int(BODY_GRACE_S / 0.05) + 5):  # drain; deferred bodies get their grace
            while self.pending:
                kind, page, obj = self.pending.popleft()
                try:
                    getattr(self, f"_do_{kind}")(page, obj)
                except Exception as exc:
                    log(f"{kind}: {type(exc).__name__}")
            if not self.deferred:
                break
            self.pending.extend(self.deferred)
            self.deferred.clear()
            self._yield()
        self.write_event({"type": "stopped", "reason": reason})
        self.write_har()
        self.state = "stopped"
        self.write_status(force=True)
        self._events.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--session-dir", required=True, type=Path)
    ap.add_argument("--headless", action="store_true",
                    help="lifecycle tests only: nobody can drive a headless window")  # fmt: skip
    args = ap.parse_args(argv)
    folder: Path = args.session_dir
    session = json.loads((folder / "session.json").read_text(encoding="utf-8"))
    config = session.get("config", {})
    from playwright.sync_api import sync_playwright

    profile = tempfile.mkdtemp(prefix="pf-observe-profile-")
    recorder: Recorder | None = None
    try:
        with sync_playwright() as pw:
            context = pw.chromium.launch_persistent_context(
                profile, headless=args.headless, channel="chromium", no_viewport=True
            )
            recorder = Recorder(context, folder, config, session=session.get("session", ""))
            recorder.profile_dir = profile
            rec = recorder

            def on_term(_sig: int, _frame: Any) -> None:
                rec.stop_requested = "stopped by a signal"

            signal.signal(signal.SIGTERM, on_term)
            panel = PanelServer(recorder, port=int(config.get("port") or 0)).start()
            recorder.ignore_origins.add(panel.origin)
            recorder.panel_url = panel.url
            recorder.write_event({"type": "started", "url": session["url"]})
            if session.get("label"):
                recorder.command("label", session["label"])
            recorder.write_status(force=True)  # pf.py observe start waits for the panel URL
            panel_page = context.pages[0] if context.pages else context.new_page()
            panel_page.goto(panel.url)
            try:
                recorder.open(session["url"])
            except Exception as exc:
                recorder.write_event({"type": "error", "message": f"could not open the URL: {exc}"})
            reason = recorder.run(float(config.get("max_session_minutes") or 60) * 60)
            recorder.stop(reason)
            panel.close()
            context.close()
    except Exception as exc:
        log(f"recorder failed: {type(exc).__name__}: {exc}")
        if recorder is not None and recorder.state != "stopped":
            recorder.stop(f"recorder error: {type(exc).__name__}")
        else:
            write_json(folder / "status.json", {"status": "failed", "error": redact.text(str(exc)),
                                                "pid": os.getpid()})  # fmt: skip
        return 1
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
