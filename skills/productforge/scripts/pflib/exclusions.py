"""Deliberate exclusions of discovered pages — ``.productforge/exclusions.json``.

A candidate URL the research will not read (duplicate, unrelated, login wall …) is excluded with a
reason, so the DISCOVERY depth gates count it as handled. Written only by ``pf.py exclude``.
"""

from __future__ import annotations

import json
from pathlib import Path

from pflib import urls, workspace
from pflib.errors import CheckFailed, UsageError
from pflib.io import atomic_write_text

FILE = "exclusions.json"


def path(ws: Path) -> Path:
    return workspace.pf_dir(ws) / FILE


def load(ws: Path) -> dict[str, dict[str, str]]:
    """Canonical URL → ``{reason, at}`` (empty when nothing was excluded)."""
    p = path(ws)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object")
        return {str(k): dict(v) for k, v in data.items()}
    except (ValueError, TypeError, OSError) as exc:
        raise CheckFailed(
            f"{FILE} is unreadable ({exc}); fix or delete .productforge/{FILE}",
            code="BAD_EXCLUSIONS_FILE",
        ) from exc


def keys(ws: Path) -> set[str]:
    """Page keys (``www.``-insensitive) of every excluded URL."""
    return {urls.page_key(u) for u in load(ws)}


def save(ws: Path, data: dict[str, dict[str, str]]) -> None:
    atomic_write_text(path(ws), json.dumps(data, indent=2, sort_keys=True) + "\n")


def add(ws: Path, raw_urls: list[str], reason: str) -> dict[str, object]:
    """Exclude ``raw_urls`` (canonicalised); logs one ``exclude`` history event."""
    reason = reason.strip()
    if not raw_urls:
        raise UsageError("exclude needs at least one URL (or --list)")
    if not reason:
        raise UsageError('exclude needs --reason "…"')
    data = load(ws)
    now = workspace.iso(workspace.utc_now())
    added: list[str] = []
    for raw in raw_urls:
        canonical = urls.canonicalize(raw)
        if canonical not in added:
            added.append(canonical)
        data[canonical] = {"reason": reason, "at": now}
    save(ws, data)
    workspace.append_history(ws, {"event": "exclude", "urls": added, "reason": reason})
    return {"excluded": added, "total": len(data)}
