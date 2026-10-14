"""Test stand-in for the user: drives the synthetic fixture site while a ``Recorder`` records it.

Runs with the observe venv's Python (Playwright), started by ``test_recorder_local_site.py``:

    <venv>/bin/python tests/observe/drive_fixture_site.py <session-dir>

It serves ``tests/fixtures/observe-site/`` (sign-in, a task list, a form, a detail page and a
WebSocket) on 127.0.0.1, attaches the shipped ``Recorder`` to a headless browser context, and
uses the shipped panel API for pause, resume and the step label. The recorder itself never
drives anything; only this test script does. Prints the secrets it typed as JSON so the test can
prove none of them reached disk.
"""

from __future__ import annotations

import base64
import hashlib
import json
import struct
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "observe"))

from playwright.sync_api import sync_playwright  # noqa: E402
from recorder import Recorder  # noqa: E402
from server import PanelServer  # noqa: E402

SITE = ROOT / "tests" / "fixtures" / "observe-site"
PAGES = {
    "/": "index.html",
    "/tasks": "tasks.html",
    "/settings": "settings.html",
    "/app.js": "app.js",
}
EMAIL = "ada.lovelace@tasklet.example"
PASSWORD = "hunter2-correct-horse"
TITLE = "Water the ferns on Thursday"
TOKEN = "eyJhbGciOiJIUzI1NiJ9.dGFza2xldC1zZXNzaW9u.c2lnbmF0dXJlLXZhbHVlLWhlcmU"
MEMBERS = {
    "7": {"name": "Ada Lovelace", "email": EMAIL, "role": "owner"},
    "8": {"name": "Grace Hopper", "email": "grace@tasklet.example", "role": "member"},
}
TASKS = [{"id": 101, "title": "Plan the sprint", "due": "2026-10-20", "done": False},
         {"id": 102, "title": "Ship the release", "due": None, "done": True}]  # fmt: skip
GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def recv_exact(sock: Any, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("closed")
        buf += chunk
    return buf


def ws_send(sock: Any, text: str) -> None:
    data = text.encode()
    head = (
        bytes([0x81, len(data)])
        if len(data) < 126
        else bytes([0x81, 126]) + struct.pack(">H", len(data))
    )
    sock.sendall(head + data)


def ws_serve(handler: BaseHTTPRequestHandler) -> None:
    key = handler.headers["Sec-WebSocket-Key"]
    accept = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
    handler.send_response(101)
    handler.send_header("Upgrade", "websocket")
    handler.send_header("Connection", "Upgrade")
    handler.send_header("Sec-WebSocket-Accept", accept)
    handler.end_headers()
    sock = handler.connection
    try:
        while True:
            b1, b2 = recv_exact(sock, 2)
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack(">H", recv_exact(sock, 2))[0]
            elif length == 127:
                length = struct.unpack(">Q", recv_exact(sock, 8))[0]
            mask = recv_exact(sock, 4) if b2 & 0x80 else b"\0\0\0\0"
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(recv_exact(sock, length)))
            if b1 & 0x0F == 8:
                sock.sendall(b"\x88\x00")
                return
            msg = json.loads(data)
            ws_send(sock, json.dumps({"type": "subscribed", "channel": msg.get("channel")}))
            created = {"type": "task.created", "task": {"id": 103, "title": TITLE, "due": None}}
            ws_send(sock, json.dumps(created))
    except (ConnectionError, OSError, ValueError):
        return
    finally:
        handler.close_connection = True


class Site(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def _send(
        self, code: int, body: bytes, ctype: str, extra: dict[str, str] | None = None
    ) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data: Any, extra: dict[str, str] | None = None) -> None:
        self._send(200, json.dumps(data).encode(), "application/json", extra)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?")[0]
        if path == "/ws":
            ws_serve(self)
        elif path in PAGES:
            ctype = "text/javascript" if path.endswith(".js") else "text/html; charset=utf-8"
            self._send(200, (SITE / PAGES[path]).read_bytes(), ctype)
        elif path.startswith("/tasks/"):
            self._send(200, (SITE / "task.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/tasks":
            self._json(TASKS)
        elif path == "/api/members":
            self._json(MEMBERS)
        elif path == "/api/settings":  # this account is a member, not an owner
            body = json.dumps({"error": "forbidden", "required_role": "owner"}).encode()
            self._send(403, body, "application/json")
        elif path.startswith("/api/tasks/"):
            self._json(TASKS[0])
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if self.path == "/api/session":
            self._json({"user": {"id": 7, "name": "Ada", "role": "owner"}, "token": TOKEN},
                       {"Set-Cookie": f"sid={TOKEN}; HttpOnly; Path=/"})  # fmt: skip
        elif self.path == "/api/tasks":
            self._json(
                {"id": 103, "title": body.get("title"), "due": body.get("due"), "done": False}
            )
        elif self.path == "/graphql":
            self._json({"data": {"counts": {"open": 1, "done": 1}, "me": {"email": EMAIL}}})
        else:
            self._send(404, b"not found", "text/plain")


def panel_api(panel: PanelServer, name: str, body: dict[str, Any] | None = None) -> None:
    req = urllib.request.Request(
        f"{panel.origin}/api/{name}", data=json.dumps(body or {}).encode(), method="POST",
        headers={"X-PF-Token": panel.token, "Content-Type": "application/json"},
    )  # fmt: skip
    with urllib.request.urlopen(req, timeout=5) as res:
        assert res.status == 200


def short_session(folder: Path, mode: str) -> int:
    """Open the sign-in page once with ``observe.screenshots = mode`` and stop."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Site)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, channel="chromium")
        rec = Recorder(browser.new_context(), folder,
                       {"allowed_hosts": ["127.0.0.1"], "screenshots": mode})  # fmt: skip
        page = rec.open(f"http://127.0.0.1:{httpd.server_address[1]}/")
        page.fill("#password", PASSWORD)
        for _ in range(12):
            page.wait_for_timeout(150)
            rec.pump()
        rec.stop("test finished")
        browser.close()
    httpd.shutdown()
    print(json.dumps({"mode": mode}))
    return 0


def main(folder: Path) -> int:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Site)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, channel="chromium")
        context = browser.new_context()
        rec = Recorder(context, folder, {"allowed_hosts": ["127.0.0.1"], "screenshots": "on"})
        panel = PanelServer(rec).start()
        rec.ignore_origins.add(panel.origin)
        page = rec.open(base + "/")  # the shipped way to open a tab: capture attached first

        def settle(rounds: int = 8) -> None:
            for _ in range(rounds):
                page.wait_for_timeout(150)
                rec.pump()

        settle()
        page.fill("#email", EMAIL)
        page.fill("#password", PASSWORD)
        page.click("#sign-in")
        page.wait_for_url("**/tasks")
        page.wait_for_selector("li.task")
        settle()
        page.click("#owner-line")  # plain text: where it was clicked is kept, never what it says
        page.fill("#title", TITLE)
        page.fill("#due", "2026-11-01")
        page.click("#new-task button[type=submit]")
        page.wait_for_selector("text=A task was added")
        settle()
        panel_api(panel, "pause")
        settle()
        page.click("#refresh")  # while paused: neither the click nor its request is recorded
        settle()
        panel_api(panel, "resume")
        panel_api(panel, "label", {"label": "Open a task"})
        settle()
        page.click("a.task-link >> nth=0")
        page.wait_for_url("**/tasks/101")
        settle()
        panel_api(panel, "label", {"label": "Open settings"})
        page.goto(base + "/tasks")
        page.wait_for_selector("li.task")
        settle()
        page.click("nav >> text=Settings")
        page.wait_for_selector("text=Only owners can edit")
        settle(12)
        rec.stop("test finished")
        panel.close()
        browser.close()
    httpd.shutdown()
    secrets = [
        EMAIL,
        PASSWORD,
        TITLE,
        TOKEN,
        "hunter2",
        "Ada Lovelace",
        "Grace Hopper",
        "grace@tasklet.example",
        "Plan the sprint",
        "Ship the release",
        "personal",
    ]
    print(json.dumps({"base": base, "secrets": secrets}))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 2:
        sys.exit(short_session(Path(sys.argv[1]), sys.argv[2]))
    sys.exit(main(Path(sys.argv[1])))
