"""Stand-in for observe/recorder.py in lifecycle tests: writes status.json, waits for stop."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

folder = Path(sys.argv[sys.argv.index("--session-dir") + 1])


def status(state: str) -> None:
    data = {"status": state, "pid": os.getpid(), "counts": {"events": 1},
            "panel_url": "http://127.0.0.1:9/?t=test", "label": None}  # fmt: skip
    (folder / "status.json").write_text(json.dumps(data))


if os.environ.get("PF_FAKE_RECORDER_FAIL"):
    print("playwright exploded", flush=True)
    sys.exit(3)
status("recording")
deadline = time.monotonic() + 30
ignore_stop = bool(os.environ.get("PF_FAKE_RECORDER_IGNORE_STOP"))
while time.monotonic() < deadline and (ignore_stop or not (folder / "stop.request").exists()):
    time.sleep(0.05)
status("stopped")
