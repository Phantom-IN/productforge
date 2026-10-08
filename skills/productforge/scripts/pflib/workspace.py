"""Workspace location, staging runs, history log and ID high-water marks.

A workspace is any directory containing ``.productforge/`` (IMPLEMENTATION_PLAN.md §5).
Full initialisation (state.json, config.json, scaffolding) arrives in Phase 02.
"""

from __future__ import annotations

import json
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pflib.errors import UsageError
from pflib.io import atomic_write_text

PF_DIR = ".productforge"
STAGING = "staging"
MERGED = "_merged"
RAW = "raw"  # delegated-provider output inside a run; never merged (§9.4)
CACHE = "cache"  # .productforge/cache/ (discover results, …)
RUN_META = ".run.json"
HISTORY = "history.log"
IDS_FILE = "ids.json"
MERGE_LOCK = "merge.lock"

ROLE_RE = re.compile(r"^[a-z][a-z0-9-]{1,40}$")
RUN_ID_RE = re.compile(r"^\d{8}T\d{6}Z?-[a-z][a-z0-9-]*-[0-9a-f]{4}$")


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def find_workspace(start: Path) -> Path | None:
    """Nearest ancestor of ``start`` (inclusive) that contains ``.productforge/``."""
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / PF_DIR).is_dir():
            return candidate
    return None


def resolve_workspace(explicit: str | None, cwd: Path | None = None) -> Path:
    """Workspace from ``--workspace`` or discovery; raises ``UsageError`` if none."""
    if explicit:
        ws = Path(explicit).resolve()
        if not (ws / PF_DIR).is_dir():
            raise UsageError(
                f"{ws} is not a ProductForge workspace (no {PF_DIR}/)", code="NO_WORKSPACE"
            )
        return ws
    found = find_workspace(cwd or Path.cwd())
    if found is None:
        raise UsageError(
            "No ProductForge workspace found (start one with /productforge <url>)",
            code="NO_WORKSPACE",
        )
    return found


def pf_dir(ws: Path) -> Path:
    return ws / PF_DIR


def staging_root(ws: Path) -> Path:
    return pf_dir(ws) / STAGING


def staging_dir(ws: Path, run_id: str) -> Path:
    if not RUN_ID_RE.match(run_id):
        raise UsageError(f"invalid run id {run_id!r}", code="BAD_RUN_ID")
    return staging_root(ws) / run_id


def new_run_id(role: str, now: datetime | None = None) -> str:
    if not ROLE_RE.match(role):
        raise UsageError(
            f"invalid role {role!r} (lowercase letters, digits, dashes)", code="BAD_ROLE"
        )
    stamp = (now or utc_now()).strftime("%Y%m%dT%H%M%S")
    return f"{stamp}-{role}-{secrets.token_hex(2)}"


def create_staging_run(ws: Path, role: str) -> tuple[str, Path]:
    now = utc_now()
    for _ in range(5):
        run_id = new_run_id(role, now)
        path = staging_dir(ws, run_id)
        if not path.exists() and not (staging_root(ws) / MERGED / run_id).exists():
            path.mkdir(parents=True)
            meta = {"run_id": run_id, "role": role, "created_at": iso(now)}
            atomic_write_text(path / RUN_META, json.dumps(meta, indent=2) + "\n")
            append_history(ws, {"event": "staging-new", "run_id": run_id, "role": role})
            return run_id, path
    raise UsageError("could not allocate a unique run id", code="BAD_RUN_ID")


def append_history(ws: Path, event: dict[str, Any]) -> None:
    """Append one JSON line to ``.productforge/history.log`` (append-only audit trail)."""
    entry = {"ts": iso(utc_now()), **event}
    with open(pf_dir(ws) / HISTORY, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=False) + "\n")


def read_history(ws: Path) -> list[dict[str, Any]]:
    path = pf_dir(ws) / HISTORY
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def load_id_marks(ws: Path) -> dict[str, int]:
    """Highest ID number ever allocated per prefix (so IDs are never reused)."""
    path = pf_dir(ws) / IDS_FILE
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): int(v) for k, v in data.items()}


def save_id_marks(ws: Path, marks: dict[str, int]) -> None:
    atomic_write_text(
        pf_dir(ws) / IDS_FILE, json.dumps(dict(sorted(marks.items())), indent=2) + "\n"
    )
