"""Domain model and permissions grammar (IMPLEMENTATION_PLAN.md §12.4–§12.5).

An entity's ``Relationships`` field lists ``;``-separated links from this entity to another::

    - Relationships: E-01 (N:1, required) workspace; E-02 (N:1, optional) assignee

Cardinality reads *this : other* (``N:1`` — many of this belong to one of the other) and
``required`` means this entity cannot exist without the link. ``none`` means no links.

A permission rule's ``Grants`` field gives one cell per role, ``,``-separated::

    - Grants: RL-01 ✓, RL-02 ✓, RL-03 Limited, RL-04 ?

Cells are ``✓`` (allowed), ``✗`` (denied), ``Limited`` (explained in ``Limited means``) and ``?``
(unknown — explained by a ``Related unknown`` U record).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pflib import records
from pflib.index import WorkspaceIndex

CARDINALITIES = ("1:1", "1:N", "N:1", "N:M")
INVERSE = {"1:1": "1:1", "1:N": "N:1", "N:1": "1:N", "N:M": "N:M"}
REL_RE = re.compile(
    r"^(?P<id>E-\??\d+) \((?P<card>[1NM]:[1NM]), (?P<req>required|optional)\)(?: (?P<note>.+))?$"
)
NONE = "none"

DELETION_KINDS = ("cascade", "soft-delete", "archive", "restrict", "orphan-allowed")

CELLS = ("✓", "✗", "Limited", "?")
GRANT_RE = re.compile(r"^(?P<id>RL-\??\d+)\s*(?:→|:)?\s*(?P<cell>✓|✗|Limited|\?)$")
ACTION_ORDER = ("create", "read", "update", "delete", "manage")

# Feature names that imply an entity is changed by users (with Mutable fields: needs PR rules).
MUTATING = ("create", "add", "edit", "update", "delete", "remove", "assign", "invite", "archive",
            "upload", "attach", "comment", "move", "rename", "manage")  # fmt: skip


@dataclass(frozen=True)
class Relationship:
    target: str
    cardinality: str
    required: bool
    note: str


def parse_relationships(value: str) -> tuple[list[Relationship], list[str]]:
    """Relationships and the parts that do not follow the grammar."""
    text = value.strip()
    if not text or text.lower() == NONE:
        return [], []
    rels: list[Relationship] = []
    bad: list[str] = []
    for part in (p.strip() for p in text.split(";")):
        if not part:
            continue
        m = REL_RE.match(part)
        if not m or m.group("card") not in CARDINALITIES:
            bad.append(part)
            continue
        rels.append(
            Relationship(m.group("id"), m.group("card"), m.group("req") == "required",
                         (m.group("note") or "").strip())
        )  # fmt: skip
    return rels, bad


def deletion_kind(value: str) -> str | None:
    """The deletion keyword a ``Deletion semantics`` value starts with (free text may follow)."""
    head = value.strip().lower()
    return next((k for k in DELETION_KINDS if re.match(rf"{re.escape(k)}\b", head)), None)


def parse_grants(value: str) -> tuple[dict[str, str], list[str]]:
    """Role → cell, and the parts that do not follow the grammar."""
    cells: dict[str, str] = {}
    bad: list[str] = []
    for part in (p.strip() for p in value.split(",")):
        if not part:
            continue
        m = GRANT_RE.match(part)
        if not m:
            bad.append(part)
            continue
        cells[m.group("id")] = m.group("cell")
    return cells, bad


def active(index: WorkspaceIndex, prefix: str) -> list[records.Record]:
    return sorted((r for _, r in index.records(prefix) if records.is_active(r)), key=lambda r: r.id)


def tree_parent(entity: records.Record, known: set[str]) -> str | None:
    """The containing entity: the first required N:1 link to another known entity."""
    rels, _ = parse_relationships(entity.get("Relationships"))
    return next(
        (r.target for r in rels
         if r.cardinality == "N:1" and r.required and r.target in known and r.target != entity.id),
        None,
    )  # fmt: skip


def relationship_tree(index: WorkspaceIndex) -> list[str]:
    """Markdown tree lines: roots are entities with no required N:1 parent (tenancy first)."""
    ents = active(index, "E")
    by_id = {e.id: e for e in ents}
    known = set(by_id)
    children: dict[str, list[records.Record]] = {}
    roots: list[records.Record] = []
    for e in ents:
        parent = tree_parent(e, known)
        if parent is None:
            roots.append(e)
        else:
            children.setdefault(parent, []).append(e)
    lines: list[str] = []
    seen: set[str] = set()

    def walk(e: records.Record, depth: int) -> None:
        if e.id in seen:
            return
        seen.add(e.id)
        rels, _ = parse_relationships(e.get("Relationships"))
        parent = tree_parent(e, known)
        extra = [
            f"{r.target} {by_id[r.target].title} ({r.cardinality})"
            for r in rels
            if r.target in known and r.target != parent and r.cardinality in ("N:1", "N:M")
        ]
        suffix = f" · also {', '.join(extra)}" if extra else ""
        lines.append(f"{'  ' * depth}- {e.id} {e.title}{suffix}")
        for child in sorted(children.get(e.id, []), key=lambda r: r.id):
            walk(child, depth + 1)

    for root in roots:
        walk(root, 0)
    for e in ents:  # entities caught in a parent cycle: shown at the top level, never hidden
        if e.id not in seen:
            walk(e, 0)
    return lines


# Words that name UI state rather than a thing with its own identity (v1 dogfood: "dashboard filter
# state", "per-user view preference", "rolling traffic summary").
UI_STATE_WORDS = ("preference", "selection", "filter state", "view state", "ui state", "layout",
                  "panel", "widget", "toggle", "sort order", "summary",
                  "display setting")  # fmt: skip


def looks_like_ui_state(entity: records.Record) -> str | None:
    """The UI-state word an entity's name uses, if any (a hint, not a rule)."""
    name = entity.title.lower()
    return next((w for w in UI_STATE_WORDS if re.search(rf"\b{re.escape(w)}s?\b", name)), None)


def is_mutable(entity: records.Record, features: dict[str, records.Record]) -> bool:
    """Users change it: it lists mutable fields, or a linked feature's name says so."""
    mutable = entity.get("Mutable fields").strip().lower()
    if mutable and not re.match(rf"{NONE}\b", mutable):  # "none — append-only" is immutable
        return True
    for fid in records.parse_refs(entity.get("Features")):
        f = features.get(fid)
        name = (f.get("Feature").strip() or f.title).lower() if f else ""
        if any(word in name for word in MUTATING):
            return True
    return False


def _action_key(action: str) -> tuple[int, str]:
    a = action.strip().lower()
    return (ACTION_ORDER.index(a) if a in ACTION_ORDER else len(ACTION_ORDER), a)


def matrix_rows(index: WorkspaceIndex) -> tuple[list[records.Record], list[records.Record]]:
    """Active roles (columns) and active rules sorted by resource then action (rows)."""
    rules = sorted(
        active(index, "PR"),
        key=lambda r: (next(iter(records.parse_refs(r.get("Resource"))), ""),
                       _action_key(r.get("Action")), r.id),
    )  # fmt: skip
    return active(index, "RL"), rules


def permission_gaps(index: WorkspaceIndex) -> list[dict[str, Any]]:
    """Every active rule with ``?`` cells: which roles, and the unknowns that explain them."""
    roles, rules = matrix_rows(index)
    names = {r.id: r.title for r in roles}
    unknowns = {u.id: u for _, u in index.records("U")}
    out = []
    for rule in rules:
        cells, _ = parse_grants(rule.get("Grants"))
        unknown_roles = [rid for rid in (r.id for r in roles) if cells.get(rid) == "?"]
        if not unknown_roles:
            continue
        uids = records.parse_refs(rule.get("Related unknown"))
        out.append({
            "rule": rule.id,
            "title": rule.title,
            "resource": next(iter(records.parse_refs(rule.get("Resource"))), ""),
            "action": rule.get("Action").strip(),
            "roles": [f"{rid} {names[rid]}" for rid in unknown_roles],
            "unknowns": [{"id": u, "question": unknowns[u].get("Question").strip()}
                         for u in uids if u in unknowns],
            "evidence": records.parse_refs(rule.get("Evidence")),
        })  # fmt: skip
    return out


def permission_cells(index: WorkspaceIndex) -> dict[str, Any]:
    """Cell counts over active rules × active roles (missing = no cell for a role)."""
    roles, rules = matrix_rows(index)
    counts = dict.fromkeys(CELLS, 0)
    missing = 0
    for rule in rules:
        cells, _ = parse_grants(rule.get("Grants"))
        for role in roles:
            cell = cells.get(role.id)
            if cell is None:
                missing += 1
            else:
                counts[cell] += 1
    return {"rules": len(rules), "roles": len(roles), "cells": counts, "missing": missing}
