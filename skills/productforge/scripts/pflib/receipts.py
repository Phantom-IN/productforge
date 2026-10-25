"""Agent input receipts.

A brief lists the workspace files an agent must read. The agent's summary carries one
``READ <workspace path>: <n>`` line per input (``n`` = records for record artifacts and
directories, ``##`` sections for prose files). Preflight compares the lines with the real
counts. These findings are preflight-only (warn); they are not validator codes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pflib import catalog, records, workspace

MISSING = "INPUT_RECEIPT_MISSING"
SHORT = "INPUT_RECEIPT_SHORT"
THRESHOLD = 0.9  # a receipt below this share of the expected count is short

BRIEF_INPUTS = ".brief.json"  # inside a staging run; dot-files are never merged
READ_RE = re.compile(r"^\s*READ\s+(?P<path>\S+?):\s*(?P<n>\d+)", re.M)
SECTION_RE = re.compile(r"^## \S", re.M)


def _count_records(text: str) -> int:
    return sum(1 for line in text.splitlines() if records.RECORD_HEAD_RE.match(line))


def kind_and_expected(ws: Path, rel: str) -> tuple[str, int]:
    """``(kind, expected count)`` of one workspace input; a missing file expects 0."""
    path = ws / rel
    if path.is_dir():
        files = sorted(path.rglob("*.md"))
        return "directory", sum(_count_records(f.read_text(encoding="utf-8")) for f in files)
    spec = catalog.spec_for_path(rel)
    if spec is not None and spec.is_glob:
        files = sorted(ws.glob(rel))
        return "directory", sum(_count_records(f.read_text(encoding="utf-8")) for f in files)
    if not path.is_file():
        return ("records" if spec is not None and spec.schemas else "prose"), 0
    if path.suffix == ".json":
        return "json", 1
    text = path.read_text(encoding="utf-8")
    if spec is not None and spec.schemas:
        return "records", _count_records(text)
    return "prose", len(SECTION_RE.findall(text))


def describe(ws: Path, rels: list[str]) -> list[dict[str, Any]]:
    out = []
    for rel in rels:
        kind, expected = kind_and_expected(ws, rel)
        out.append({"path": rel, "kind": kind, "expected": expected})
    return out


def size_kb(ws: Path, rels: list[str]) -> float:
    total = 0
    for rel in rels:
        path = ws / rel
        if path.is_dir():
            total += sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        elif path.is_file():
            total += path.stat().st_size
    return round(total / 1024, 1)


def save_inputs(run_dir: Path, rels: list[str]) -> None:
    (run_dir / BRIEF_INPUTS).write_text(json.dumps({"inputs": rels}), encoding="utf-8")


def _inside(ws: Path, rel: str) -> bool:
    """The input resolves inside the workspace (no absolute path, no ``..`` escape)."""
    try:
        (ws / rel).resolve().relative_to(ws.resolve())
    except ValueError:
        return False
    return True


def load_inputs(run_dir: Path, ws: Path | None = None) -> list[str]:
    """The recorded inputs; with ``ws``, only those that resolve inside the workspace."""
    path = run_dir / BRIEF_INPUTS
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        rels = [str(x) for x in data.get("inputs", [])]
        return [r for r in rels if ws is None or _inside(ws, _normalise(ws, r))]
    except (ValueError, AttributeError, TypeError, OSError):
        return []


def _normalise(ws: Path, value: str) -> str:
    prefix = str(ws).rstrip("/") + "/"
    if value.startswith(prefix):
        value = value[len(prefix) :]
    return value.removeprefix("./").rstrip("/")


def parse(ws: Path, summary: str) -> dict[str, int]:
    """Receipts by normalised workspace path (the last line wins)."""
    return {_normalise(ws, m["path"]): int(m["n"]) for m in READ_RE.finditer(summary)}


def summary_text(run_dir: Path, summary_file: Path | None) -> str | None:
    path = summary_file or run_dir / workspace.SUMMARY
    return path.read_text(encoding="utf-8") if path.is_file() else None


def check(ws: Path, run_dir: Path, summary: str | None) -> list[dict[str, Any]]:
    """Receipt findings (``warn``) for the brief inputs recorded in ``run_dir``."""
    rels = load_inputs(run_dir, ws)
    got = parse(ws, summary or "")
    found: list[dict[str, Any]] = []
    for item in describe(ws, [_normalise(ws, r) for r in rels]):
        rel, expected = item["path"], item["expected"]
        if rel not in got:
            found.append(
                _finding(
                    MISSING,
                    rel,
                    f"the summary has no `READ {rel}: <n>` line (expected about {expected} "
                    f"{_unit(item['kind'])}); read the input and report how much you read",
                )
            )
        elif expected and got[rel] < THRESHOLD * expected:
            found.append(
                _finding(
                    SHORT,
                    rel,
                    f"the summary says READ {rel}: {got[rel]} but the input holds {expected} "
                    f"{_unit(item['kind'])}; read the rest and report a fresh count",
                )
            )
    return found


def _unit(kind: str) -> str:
    return {"prose": "sections", "json": "file"}.get(kind, "records")


def _finding(code: str, rel: str, message: str) -> dict[str, Any]:
    return {
        "code": code,
        "severity": "warn",
        "artifact": rel,
        "record_id": None,
        "message": message,
    }
