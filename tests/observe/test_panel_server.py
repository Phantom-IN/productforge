"""The control panel binds to 127.0.0.1 and refuses requests without the token or a local Host."""

from __future__ import annotations

import http.client
import json
from collections.abc import Iterator
from typing import Any

import pytest
from server import PanelServer


class FakeRecorder:
    def __init__(self) -> None:
        self.commands: list[tuple[str, str | None]] = []

    def status(self) -> dict[str, Any]:
        return {"status": "recording", "counts": {"events": 3}}

    def command(self, name: str, arg: str | None = None) -> None:
        self.commands.append((name, arg))


@pytest.fixture
def panel() -> Iterator[tuple[PanelServer, FakeRecorder]]:
    rec = FakeRecorder()
    server = PanelServer(rec).start()
    yield server, rec
    server.close()


def call(server: PanelServer, method: str, path: str, *, token: str | None = None,
         host: str | None = None, body: Any = None,
         origin: str | None = None) -> tuple[int, bytes]:  # fmt: skip
    conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
    headers = {"Host": host or f"127.0.0.1:{server.port}"}
    if token is not None:
        headers["X-PF-Token"] = token
    if origin is not None:
        headers["Origin"] = origin
    data = json.dumps(body).encode() if body is not None else None
    if data is not None:
        headers["Content-Type"] = "application/json"
    conn.request(method, path, body=data, headers=headers)
    res = conn.getresponse()
    out = (res.status, res.read())
    conn.close()
    return out


def test_binds_to_localhost_only(panel: tuple[PanelServer, FakeRecorder]) -> None:
    server, _ = panel
    assert server.httpd.server_address[0] == "127.0.0.1"
    assert server.url.startswith(f"http://127.0.0.1:{server.port}/?t=")


def test_status_needs_the_token(panel: tuple[PanelServer, FakeRecorder]) -> None:
    server, _ = panel
    assert call(server, "GET", "/api/status")[0] == 403
    assert call(server, "GET", "/api/status", token="wrong")[0] == 403
    code, body = call(server, "GET", "/api/status", token=server.token)
    assert code == 200 and json.loads(body)["status"] == "recording"


def test_foreign_host_and_origin_are_refused(panel: tuple[PanelServer, FakeRecorder]) -> None:
    server, rec = panel
    assert call(server, "GET", "/api/status", token=server.token, host="evil.example")[0] == 403
    code, _ = call(server, "POST", "/api/stop", token=server.token, body={},
                   origin="https://product.example")  # fmt: skip
    assert code == 403 and rec.commands == []


def test_page_needs_the_token_and_carries_it_to_the_script(
    panel: tuple[PanelServer, FakeRecorder],
) -> None:
    server, _ = panel
    assert call(server, "GET", "/")[0] == 403
    code, html = call(server, "GET", f"/?t={server.token}")
    assert code == 200 and f"panel.js?t={server.token}".encode() in html
    assert call(server, "GET", f"/panel.js?t={server.token}")[0] == 200


def test_commands_are_queued_for_the_recorder(panel: tuple[PanelServer, FakeRecorder]) -> None:
    server, rec = panel
    for name in ("pause", "resume"):
        assert call(server, "POST", f"/api/{name}", token=server.token, body={})[0] == 200
    long = "x" * 500
    assert call(server, "POST", "/api/label", token=server.token, body={"label": long})[0] == 200
    assert call(server, "POST", "/api/click", token=server.token, body={})[0] == 404
    assert rec.commands == [("pause", None), ("resume", None), ("label", "x" * 120)]
