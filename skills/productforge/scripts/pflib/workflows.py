"""Workflow files: step grammar and candidate generation.

A workflow file is one ``W-`` record followed by prose sections; ``## Steps`` holds numbered steps:

    1. [observed] User opens the task composer — D-019, S-001
    2. [implied-system] Task is persisted and an activity entry is written
       — F-010

An indented line continues the step above it. ``[observed]`` steps are what public evidence
shows; ``[implied-system]`` steps are the system behaviour such a flow requires (persist,
authorize, index, notify, …) — engineering inferences that feed architecture inference later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pflib import catalog, config, records
from pflib.index import WorkspaceIndex

TAGS = ("observed", "implied-system")
STEP_RE = re.compile(r"^(?P<n>\d+)\. \[(?P<tag>[a-z-]+)\] (?P<text>.+?)(?: — (?P<refs>.+))?$")
NUMBERED_RE = re.compile(r"^\d+\.\s")


@dataclass(frozen=True)
class Step:
    number: int
    tag: str
    text: str
    refs: tuple[str, ...]
    line: str


def steps_section(text: str) -> str | None:
    return records.parse_document(text).section_text("Steps")


def _logical_lines(body: str) -> list[str]:
    """Lines with indented continuations joined to the step above (a wrapped list item)."""
    out: list[str] = []
    for line in body.splitlines():
        if out and line[:1] in (" ", "\t") and line.strip() and NUMBERED_RE.match(out[-1]):
            out[-1] = f"{out[-1].rstrip()} {line.strip()}"
        else:
            out.append(line)
    return out


def parse_steps(text: str) -> tuple[list[Step], list[str]]:
    """Steps of a workflow file and the numbered lines that do not follow the grammar."""
    body = steps_section(text)
    if body is None:
        return [], []
    steps: list[Step] = []
    bad: list[str] = []
    for line in _logical_lines(body):
        if not NUMBERED_RE.match(line):
            continue
        m = STEP_RE.match(line)
        if not m or m.group("tag") not in TAGS:
            bad.append(line)
            continue
        refs = tuple(records.parse_refs(m.group("refs") or ""))
        steps.append(Step(int(m.group("n")), m.group("tag"), m.group("text"), refs, line))
    return steps, bad


def requirements_surfaced(text: str) -> list[str]:
    """Bullet lines under ``## Engineering requirements surfaced`` (``none`` means none)."""
    body = records.parse_document(text).section_text("Engineering requirements surfaced") or ""
    items = [ln[2:].strip() for ln in body.splitlines() if ln.startswith("- ")]
    return [i for i in items if i and i.lower() != "none"]


def has_system_steps(text: str) -> bool:
    steps, _ = parse_steps(text)
    return any(s.tag == "implied-system" for s in steps)


# ------------------------------------------------------------------------- candidates

# feature-name keyword → action verb for a candidate workflow
KEYWORDS: tuple[tuple[str, str], ...] = (
    ("assign", "Assign"), ("invite", "Invite"), ("invitation", "Invite"), ("search", "Search"),
    ("connect", "Connect"), ("integration", "Connect"), ("sync", "Connect"), ("export", "Export"),
    ("import", "Import"), ("comment", "Comment"), ("notif", "Get notified"),
    ("share", "Share"), ("sharing", "Share"), ("archive", "Archive"), ("filter", "Filter"),
    ("schedul", "Schedule"), ("embed", "Embed"), ("sign-in", "Sign in"), ("sign in", "Sign in"),
    ("login", "Sign in"), ("billing", "Manage billing"), ("upgrade", "Upgrade"),
    ("webhook", "Configure"), ("token", "Create"), ("report", "Run"), ("alert", "Configure"),
)  # fmt: skip


def _active_features(index: WorkspaceIndex) -> list[records.Record]:
    return [rec for _, rec in index.records("F") if records.is_active(rec)]


def candidates(ws: Path) -> dict[str, Any]:
    """Deterministic workflow candidates from the feature matrix (scripts propose, users trim)."""
    index = WorkspaceIndex(ws)
    feats = _active_features(index)
    covered = {
        ref
        for _, w in index.records("W")
        if records.is_active(w)
        for ref in records.parse_refs(w.get("Features"))
    }
    by_name: dict[str, dict[str, Any]] = {}

    def add(name: str, domain: str, fid: str, reason: str) -> None:
        key = records.normalise_text(name)
        entry = by_name.setdefault(
            key, {"name": name, "domain": domain, "features": [], "reason": reason}
        )
        if fid not in entry["features"]:
            entry["features"].append(fid)

    for f in sorted(feats, key=lambda r: r.id):
        if f.id in covered:
            continue
        name = f.get("Feature").strip() or f.title
        domain = f.get("Domain").strip()
        lowered = name.lower()
        verb = next((v for k, v in KEYWORDS if k in lowered), None)
        if verb:
            words = records.normalise_text(name).split()
            said = all(  # "Comment" + "Comments" → just "Comments"
                any(w.startswith(v) for w in words) for v in records.normalise_text(verb).split()
            )
            add(name if said else f"{verb} — {name}", domain, f.id, "feature keyword")
        elif not records.parse_refs(f.get("Parent")):
            add(f"Create and manage — {name}", domain, f.id, "top-level feature")
        if re.search(r"\b(flow|workflow|wizard|onboarding)\b", f.get("Notes"), re.I):
            add(f"{name} flow", domain, f.id, "notes mention a flow")
    from pflib.conditions_product_model import CORE_DOMAIN_MIN_FEATURES  # lazy: gates load stages

    cap = int(config.resolve("model.max_workflows", ws))
    existing = len(index.records("W"))
    sizes: dict[str, int] = {}
    for f in feats:
        d = f.get("Domain").strip()
        if d:
            sizes[d] = sizes.get(d, 0) + 1
    order = sorted(sizes, key=lambda d: (-sizes[d], d))  # core domains first
    domain_of = {f.id: f.get("Domain").strip() for f in feats}
    has_workflow = {domain_of[ref] for ref in covered if ref in domain_of}
    required = [d for d in order if sizes[d] >= CORE_DOMAIN_MIN_FEATURES and d not in has_workflow]
    per_domain: dict[str, list[dict[str, Any]]] = {}
    for entry in sorted(by_name.values(), key=lambda e: (e["domain"], e["features"][0], e["name"])):
        per_domain.setdefault(entry["domain"], []).append(entry)
    chosen: list[dict[str, Any]] = []
    for d in required:  # the gate needs one per core domain: never dropped by the cap
        if per_domain.get(d):
            chosen.append(per_domain[d].pop(0))
            continue
        first = min((f for f in feats if f.get("Domain").strip() == d), key=lambda r: r.id)
        name = first.get("Feature").strip() or first.title
        chosen.append(
            {
                "name": f"Create and manage — {name}",
                "domain": d,
                "features": [first.id],
                "reason": "core domain without a workflow",
            }
        )
    room = max(0, cap - existing)
    effective_cap = cap
    below = len(required) > room
    if below:
        effective_cap = existing + len(required)
        room = len(required)
    rotation = [d for d in order if d in per_domain] + sorted(set(per_domain) - set(order))
    while len(chosen) < room and any(per_domain.values()):
        for d in rotation:  # round-robin over domains, biggest first
            if per_domain.get(d) and len(chosen) < room:
                chosen.append(per_domain[d].pop(0))
    result: dict[str, Any] = {
        "candidates": chosen,
        "cap": cap,
        "effective_cap": effective_cap,
        "existing_workflows": existing,
        "required_domains": required,
        "remaining_candidates": sum(len(v) for v in per_domain.values()),
        "features_covered": sorted(covered),
    }
    if below:
        result["cap_below_required"] = len(required)
    return result


def workflow_files(ws: Path) -> list[Path]:
    (spec,) = catalog.specs_for_prefix("W")
    return sorted(p for p in ws.glob(spec.path) if p.is_file())
