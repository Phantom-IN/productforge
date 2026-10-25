"""Workspace location, staging runs, history log and ID high-water marks.

A workspace is any directory containing ``.productforge/``.
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
DISCARDED = "_discarded"
ARCHIVES = (MERGED, DISCARDED)
SUMMARY = "SUMMARY.md"  # the agent's saved reply inside a run; never merged
RAW = "raw"  # delegated-provider output inside a run; never merged
CACHE = "cache"  # .productforge/cache/ (discover results, …)
OBSERVE = "observe"  # .productforge/observe/<session>/ (observe mode; local only)
RUN_META = ".run.json"
HISTORY = "history.log"
DECISIONS = "decisions.jsonl"  # autonomous-mode decisions (append-only)
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


def update_run_meta(ws: Path, run_id: str, **fields: Any) -> dict[str, Any]:
    """Merge ``fields`` into the run's ``.run.json`` (preflight result, repair counter)."""
    path = staging_dir(ws, run_id) / RUN_META
    meta: dict[str, Any] = {}
    if path.is_file():
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    meta.update(fields)
    atomic_write_text(path, json.dumps(meta, indent=2) + "\n")
    return meta


def read_run_meta(ws: Path, run_id: str) -> dict[str, Any]:
    path = staging_dir(ws, run_id) / RUN_META
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def pending_runs(ws: Path) -> list[dict[str, Any]]:
    """Unmerged staging runs: id, role, created_at, staged .md files and records (raw/ excluded)."""
    root = staging_root(ws)
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(p for p in root.iterdir() if p.is_dir() and p.name not in ARCHIVES):
        meta_path = path / RUN_META
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
        files = [
            f for f in path.rglob("*.md")
            if not any(part.startswith(".") or part == RAW for part in f.relative_to(path).parts)
            and f.relative_to(path).as_posix() != SUMMARY
        ]  # fmt: skip
        recs = sum(
            1 for f in files for line in f.read_text(encoding="utf-8").splitlines()
            if line.startswith("### ")
        )  # fmt: skip
        raw = path / RAW
        out.append({
            "run_id": path.name,
            "role": meta.get("role"),
            "created_at": meta.get("created_at"),
            "files": len(files),
            "blocks": recs,
            "raw_files": sum(1 for f in raw.rglob("*") if f.is_file()) if raw.is_dir() else 0,
        })  # fmt: skip
    return out


def discard_run(ws: Path, run_id: str, reason: str) -> Path:
    """Move a pending run to ``staging/_discarded/`` (kept for audit; never merged)."""
    import shutil

    if not reason.strip():
        raise UsageError("discard needs a non-empty --reason", code="DISCARD_NEEDS_REASON")
    path = staging_dir(ws, run_id)
    if not path.is_dir():
        raise UsageError(f"no pending staging run {run_id!r}", code="NO_SUCH_RUN")
    dest = staging_root(ws) / DISCARDED / run_id
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(dest))
    append_history(ws, {"event": "discard", "run_id": run_id, "reason": reason.strip()})
    return dest


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
