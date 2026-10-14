"""The shipped recorder on the local fixture site (v2 phase 01). Needs the observe venv.

The venv is ``~/.productforge/observe-venv`` (``pf.py deps install browser.observe``); set
``PF_OBSERVE_VENV`` to use another one. Without it these tests are skipped.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
VENV = Path(os.environ.get("PF_OBSERVE_VENV") or Path.home() / ".productforge/observe-venv")
PYTHON = VENV / "bin" / "python"

pytestmark = pytest.mark.skipif(
    not (PYTHON.exists() and (VENV / ".productforge-ready").is_file()),
    reason="observe venv not installed (pf.py deps install browser.observe)",
)


@pytest.fixture(scope="module")
def session(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[str, Any]]:
    folder = tmp_path_factory.mktemp("obs") / "obs-20261014-120000"
    folder.mkdir()
    proc = subprocess.run(
        [str(PYTHON), str(ROOT / "tests/observe/drive_fixture_site.py"), str(folder)],
        capture_output=True, text=True, timeout=240,
    )  # fmt: skip
    assert proc.returncode == 0, proc.stderr[-2000:]
    return folder, json.loads(proc.stdout.strip().splitlines()[-1])


def events(folder: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines()]


def test_records_navigation_clicks_submit_and_realtime(
    session: tuple[Path, dict[str, Any]],
) -> None:
    folder, _ = session
    evs = events(folder)
    kinds = {e["type"] for e in evs}
    assert {"navigate", "click", "submit", "change", "request", "ws_open", "ws_message",
            "screenshot", "paused", "resumed", "label", "stopped"} <= kinds  # fmt: skip
    assert {"/", "/tasks", "/tasks/:id"} <= {e["route"] for e in evs if e["type"] == "navigate"}
    sign_in = next(e for e in evs if e["type"] == "click" and e.get("name") == "Sign in")
    assert sign_in["route"] == "/"  # where the user clicked, not where the click led
    submits = [e for e in evs if e["type"] == "submit"]
    assert {s["name"] for s in submits} == {"sign-in-form", "New task"}
    names = {f["name"] for s in submits for f in s["fields"]}
    assert {"Email", "Password", "Title", "Due date"} <= names
    ws = {(e["direction"], json.dumps(e["shape"], sort_keys=True))
          for e in evs if e["type"] == "ws_message"}  # fmt: skip
    assert ("received", json.dumps({"task": {"due": "null", "id": "number", "title": "string"},
                                    "type": "string"}, sort_keys=True)) in ws  # fmt: skip
    assert any(d == "sent" for d, _ in ws)


def test_api_shapes_and_har(session: tuple[Path, dict[str, Any]]) -> None:
    folder, _ = session
    reqs = [e for e in events(folder) if e["type"] == "request"]
    listing = next(e for e in reqs if e["route"] == "/api/tasks" and e["method"] == "GET")
    assert listing["response_shape"] == [{"done": "bool", "due": "date|null", "id": "number",
                                          "title": "string"}]  # fmt: skip
    assert listing["url"].endswith("/api/tasks?page=number&token=string")
    login = next(e for e in reqs if e["route"] == "/api/session")
    assert login["request_shape"] == {"email": "string", "password": "string"}
    assert login["response_shape"] == {"token": "string", "user": {"id": "number", "name": "string",
                                                                    "role": "string"}}  # fmt: skip
    har = json.loads((folder / "network.har").read_text())
    entries = har["log"]["entries"]
    assert any(x["request"]["method"] == "POST" for x in entries)
    for x in entries:
        names = {h["name"] for h in x["request"]["headers"] + x["response"]["headers"]}
        assert not names & {"authorization", "cookie", "set-cookie"}


def test_screens_and_screenshots(session: tuple[Path, dict[str, Any]]) -> None:
    folder, _ = session
    screens = [json.loads(p.read_text()) for p in sorted((folder / "screens").glob("*.json"))]
    assert [s["route"] for s in screens] == ["/", "/tasks", "/tasks/:id", "/settings"]
    denied = [e for e in events(folder) if e["type"] == "request" and e.get("status") == 403]
    assert [e["route"] for e in denied] == ["/api/settings"]
    sign_in = screens[0]
    assert {("Email", "email"), ("Password", "password")} <= {
        (i["name"], i["input_type"]) for i in sign_in["inputs"]
    }
    assert "Sign in" in sign_in["buttons"]
    assert {"navigation", "banner"} <= set(screens[1]["landmarks"])
    shots = sorted((folder / "shots").glob("*.png"))
    assert len(shots) >= 2 and all(p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" for p in shots)


def test_pause_records_nothing_and_labels_tag_steps(session: tuple[Path, dict[str, Any]]) -> None:
    folder, _ = session
    evs = events(folder)
    paused = next(i for i, e in enumerate(evs) if e["type"] == "paused")
    resumed = next(i for i, e in enumerate(evs) if e["type"] == "resumed")
    assert all(e["type"] != "click" for e in evs[paused:resumed])
    assert not any(e.get("name") == "Refresh" for e in evs)
    after = [e for e in evs if e["type"] == "click" and e.get("step") == "Open a task"]
    assert after and after[0]["role"] == "link"
    assert after[0]["name"] == "<item>" and after[0]["in_item"] is True  # a task title: masked
    owner = [e for e in evs if e["type"] == "click" and e.get("selector") == "p#owner-line"]
    assert owner and owner[0]["name"] == ""  # plain text clicked: its words are data


def test_graphql_id_keyed_maps_and_console_text(session: tuple[Path, dict[str, Any]]) -> None:
    folder, _ = session
    evs = events(folder)
    gql = next(e for e in evs if e.get("route") == "/graphql")
    assert gql["request_shape"] == {
        "graphql": {"fields": ["counts", "viewer"], "name": "TaskCounts", "operation": "query"},
        "variables": {"owner": "string"},
    }
    members = next(e for e in evs if e.get("route") == "/api/members")
    assert members["response_shape"] == {"<id>": {"email": "string", "name": "string",
                                                  "role": "string"}}  # fmt: skip
    sync = next(e for e in evs if e["type"] == "console_error" and "sync" in e["text"])
    assert sync["text"].endswith("/api/sync?token=string for <email>")
    tasks = json.loads((folder / "screens/002.json").read_text())
    assert {"name": "<item>", "href": tasks["links"][-1]["href"], "count": 2, "in_item": True,
            "in_nav": False} in tasks["links"]  # fmt: skip
    assert {"Tasks", "Settings"} <= {link["name"] for link in tasks["links"]}  # nav labels kept


@pytest.mark.parametrize("mode, shots", [("blur", True), ("off", False)])
def test_screenshot_policy(tmp_path: Path, mode: str, shots: bool) -> None:
    folder = tmp_path / "obs-20261014-130000"
    folder.mkdir()
    proc = subprocess.run(
        [str(PYTHON), str(ROOT / "tests/observe/drive_fixture_site.py"), str(folder), mode],
        capture_output=True, text=True, timeout=120,
    )  # fmt: skip
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert bool(list((folder / "shots").glob("*.png"))) is shots
    assert any(json.loads(line)["type"] == "navigate"
               for line in (folder / "events.jsonl").read_text().splitlines())  # fmt: skip


def test_no_typed_value_or_secret_reaches_disk(session: tuple[Path, dict[str, Any]]) -> None:
    folder, meta = session
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix != ".png":
            text = path.read_text(encoding="utf-8")
            for secret in meta["secrets"]:
                assert secret not in text, (path.name, secret)
            if path.suffix in (".jsonl", ".json"):  # (HAR headers are name/value pairs)
                assert '"value"' not in text, path.name


def test_pf_observe_start_status_stop_with_the_real_recorder(tasklet_discovery: Path) -> None:
    import functools
    import threading
    import time
    import urllib.request
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, urlsplit

    from pflib import observe

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    site = ROOT / "tests/fixtures/observe-site"
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(site)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    ws = tasklet_discovery
    observe.record_consent(ws, confirmed=True)
    try:
        out = observe.start(ws, url=f"http://127.0.0.1:{httpd.server_address[1]}/",
                            home=VENV.parent.parent, headless=True)  # fmt: skip
        panel = urlsplit(out["panel_url"])
        token = parse_qs(panel.query)["t"][0]
        req = urllib.request.Request(f"http://{panel.netloc}/api/status",
                                     headers={"X-PF-Token": token})  # fmt: skip
        with urllib.request.urlopen(req, timeout=5) as res:
            assert json.loads(res.read())["session"] == out["session"]
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if observe.session_status(ws)["counts"].get("screens"):
                break
            time.sleep(0.3)
        live = observe.session_status(ws)
        assert live["status"] == "recording" and live["counts"]["screens"] >= 1
        done = observe.stop(ws)
    finally:
        httpd.shutdown()
    assert done["status"] == "stopped"
    folder = ws / done["folder"]
    kinds = [
        json.loads(line)["type"] for line in (folder / "events.jsonl").read_text().splitlines()
    ]
    assert kinds[0] == "started" and "navigate" in kinds and kinds[-1] == "stopped"
    assert not any(e.get("route", "").startswith("/api/status") for e in events(folder))
    profile = json.loads((folder / "status.json").read_text())["profile_dir"]
    assert profile and not Path(profile).exists()  # cookies went with the temporary profile
