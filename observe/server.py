"""Observe-mode control panel server — stdlib ``http.server``.

Bound to 127.0.0.1 only. Every request must carry the session's random token (``?t=`` on the
page, ``X-PF-Token`` on the API) and a ``Host`` of 127.0.0.1/localhost on the panel's port, so a
web page open in the same browser cannot drive the panel (no CSRF, no DNS rebinding).

The server never touches Playwright: it reads ``controller.status()`` and queues commands with
``controller.command(name, arg)``; the recorder's main loop applies them.
"""

from __future__ import annotations

import hmac
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qs, urlsplit

PANEL_DIR = Path(__file__).resolve().parent / "panel"
COMMANDS = ("pause", "resume", "stop", "label")
STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/panel.js": ("panel.js", "text/javascript; charset=utf-8")}  # fmt: skip
CSP = "default-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'"
MAX_BODY = 4096


class Controller(Protocol):
    def status(self) -> dict[str, Any]: ...

    def command(self, name: str, arg: str | None = None) -> None: ...


class PanelServer:
    def __init__(self, controller: Controller, port: int = 0, token: str | None = None,
                 panel_dir: Path = PANEL_DIR) -> None:  # fmt: skip
        self.controller = controller
        self.token = token or secrets.token_urlsafe(18)
        self.panel_dir = panel_dir
        self.httpd = ThreadingHTTPServer(("127.0.0.1", port), _handler(self))
        self.httpd.daemon_threads = True
        self.port = int(self.httpd.server_address[1])
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/?t={self.token}"

    @property
    def origin(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> PanelServer:
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def host_ok(self, host: str | None) -> bool:
        return host in (f"127.0.0.1:{self.port}", f"localhost:{self.port}")

    def token_ok(self, given: str | None) -> bool:
        return bool(given) and hmac.compare_digest(given or "", self.token)


def _handler(panel: PanelServer) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "ProductForgeObserve"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 — quiet
            return

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", CSP)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, payload: dict[str, Any]) -> None:
            self._send(code, json.dumps(payload).encode("utf-8"), "application/json")

        def _guard(self, token: str | None) -> bool:
            if not panel.host_ok(self.headers.get("Host")):
                self._json(403, {"error": "bad host"})
                return False
            if not panel.token_ok(token):
                self._json(403, {"error": "bad token"})
                return False
            return True

        def do_GET(self) -> None:  # noqa: N802 — http.server API
            parts = urlsplit(self.path)
            if parts.path in STATIC:
                if not self._guard(parse_qs(parts.query).get("t", [None])[0]):
                    return
                name, ctype = STATIC[parts.path]
                body = (panel.panel_dir / name).read_bytes()
                self._send(200, body.replace(b"__TOKEN__", panel.token.encode()), ctype)
            elif parts.path == "/api/status":
                if self._guard(self.headers.get("X-PF-Token")):
                    self._json(200, panel.controller.status())
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802 — http.server API
            parts = urlsplit(self.path)
            name = parts.path.removeprefix("/api/")
            if not parts.path.startswith("/api/") or name not in COMMANDS:
                self._json(404, {"error": "not found"})
                return
            if not self._guard(self.headers.get("X-PF-Token")):
                return
            origin = self.headers.get("Origin")
            if origin is not None and origin != panel.origin:
                self._json(403, {"error": "bad origin"})
                return
            length = min(int(self.headers.get("Content-Length") or 0), MAX_BODY)
            raw = self.rfile.read(length) if length else b""
            arg = None
            if name == "label":
                try:
                    arg = str(json.loads(raw or b"{}").get("label") or "")[:120]
                except (ValueError, AttributeError):
                    self._json(400, {"error": 'label needs a JSON body {"label": …}'})
                    return
            panel.controller.command(name, arg)
            self._json(200, {"ok": True, "command": name})

    return Handler
