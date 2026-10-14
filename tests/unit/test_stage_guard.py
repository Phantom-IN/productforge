from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "hooks/stage_guard.py"
PAYLOADS = ROOT / "tests/fixtures/hooks"


def run(payload: str) -> tuple[int, dict | None, str]:  # type: ignore[type-arg]
    proc = subprocess.run(
        [sys.executable, str(GUARD)], input=payload, capture_output=True, text=True, timeout=10
    )
    out = json.loads(proc.stdout) if proc.stdout.strip() else None
    return proc.returncode, out, proc.stderr


def payload(kind: str, ws: Path, rel: str) -> str:
    text = (PAYLOADS / f"{kind}.json").read_text()
    return text.replace("{ws}", str(ws)).replace("{path}", str(ws / rel))


def denied(out: dict | None) -> str | None:  # type: ignore[type-arg]
    if out is None:
        return None
    spec = out["hookSpecificOutput"]
    assert spec["hookEventName"] == "PreToolUse" and spec["permissionDecision"] == "deny"
    return str(spec["permissionDecisionReason"])


@pytest.mark.parametrize(
    "rel, needle",
    [
        ("research/sources.md", "pf.py merge"),
        ("spec/PARITY_MATRIX.md", "pf.py merge"),
        ("research/workflows/W-001-create-a-task.md", "pf.py merge"),
        ("research/product-overview.md", "reopen DISCOVERY"),
        (".productforge/state.json", "only `pf.py`"),
        (".productforge/observe/obs-20261014-120000/events.jsonl", "only the recorder"),
        ("README.md", "PHASE_PLAN_READY, but the open stage is PRODUCT_MODEL"),
    ],
)
def test_denied_in_product_model(tasklet_product_model: Path, rel: str, needle: str) -> None:
    code, out, _ = run(payload("write", tasklet_product_model, rel))
    reason = denied(out)
    assert code == 0 and reason is not None and needle in reason, reason


@pytest.mark.parametrize(
    "rel", [".productforge/staging/run-1/research/sources.md", "apps/web/page.tsx", "notes.txt"]
)
def test_allowed(tasklet_product_model: Path, rel: str) -> None:
    code, out, _ = run(payload("edit", tasklet_product_model, rel))
    assert code == 0 and out is None


def test_open_stage_documents_are_writable(tasklet_plan: Path) -> None:
    assert run(payload("edit", tasklet_plan, "plans/README.md"))[1] is None  # phase status updates
    assert run(payload("write", tasklet_plan, "CLAUDE.md"))[1] is None
    reason = denied(run(payload("write", tasklet_plan, "spec/TRACEABILITY.md"))[1])
    assert reason is not None and "generated" in reason
    assert denied(run(payload("write", tasklet_plan, "spec/ARCHITECTURE.md"))[1]) is not None


def test_no_op_outside_a_workspace(tmp_path: Path) -> None:
    (tmp_path / "research").mkdir()
    code, out, err = run(payload("write", tmp_path, "research/sources.md"))
    assert (code, out, err) == (0, None, "")


@pytest.mark.parametrize(
    "raw",
    ["not json", "[]", '{"tool_name": "Write"}', '{"tool_name": "Write", "tool_input": "oops"}'],
)
def test_fails_open(raw: str) -> None:
    code, out, _ = run(raw)
    assert code == 0 and out is None


def test_other_tools_are_ignored(tasklet_product_model: Path) -> None:
    raw = json.dumps(
        {
            "tool_name": "Read",
            "tool_input": {"file_path": str(tasklet_product_model / "research/sources.md")},
        }
    )
    assert run(raw)[1] is None


def test_fast_enough(tasklet_product_model: Path) -> None:
    sys.path.insert(0, str(ROOT / "hooks"))
    import stage_guard

    data = json.loads(payload("write", tasklet_product_model, "research/sources.md"))
    stage_guard.decide(data)  # warm imports, as the interpreter start is not ours to measure
    start = time.perf_counter()
    for _ in range(20):
        assert stage_guard.decide(data) is not None
    assert (time.perf_counter() - start) / 20 < 0.05


def test_registered_in_hooks_json() -> None:
    config = json.loads((ROOT / "hooks/hooks.json").read_text())
    (entry,) = config["hooks"]["PreToolUse"]
    assert entry["matcher"] == "Write|Edit|MultiEdit|NotebookEdit"
    (hook,) = entry["hooks"]
    assert hook["command"] == 'python3.11 "${CLAUDE_PLUGIN_ROOT}/hooks/stage_guard.py"'
    assert hook["timeout"] == 5
