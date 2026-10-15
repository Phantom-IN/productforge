"""Repository-structure trees.

``spec/ARCHITECTURE.md`` ``## Repository structure`` holds a fenced tree of *our* repository::

    tasklet-alt/
    ├── apps/
    │   ├── web/          # Next.js UI
    │   └── api/
    └── tests/

Either box-drawing glyphs or plain indentation work; several names on one line separated by
two or more spaces are siblings, and a line holding only glyphs and a comment continues the
previous one. A single top-level directory that contains
everything else is the repository root and is dropped. Directories end with ``/``; ``#`` starts a
comment. Phase lint (Phase 15) uses ``contains`` to check that phase file paths fall inside the
declared structure.
"""

from __future__ import annotations

import re

GLYPHS = " │├└─┬┼|`+-\t "
FENCE_RE = re.compile(r"^(```|~~~)[\w-]*\n(?P<body>.*?)^\1\s*$", re.S | re.M)


class TreeError(ValueError):
    pass


def fenced_block(text: str) -> str | None:
    m = FENCE_RE.search(text)
    return m.group("body") if m else None


def parse(text: str) -> set[str]:
    """Paths declared by a tree (directories keep their trailing ``/``)."""
    entries: list[tuple[int, str]] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        col = len(line) - len(line.lstrip(GLYPHS))
        rest = line[col:].strip()
        if not rest:
            continue  # blank, or only tree glyphs before a comment continuation
        for name in re.split(r"\s{2,}", rest):  # "README.md  CLAUDE.md": siblings on one line
            if " " in name.rstrip("/"):
                raise TreeError(f"not a path: {raw.strip()!r}")
            entries.append((col, name))
    if not entries:
        raise TreeError("the tree is empty")
    stack: list[tuple[int, str]] = []
    paths: list[str] = []
    for col, name in entries:
        while stack and stack[-1][0] >= col:
            stack.pop()
        if stack and not stack[-1][1].endswith("/"):
            raise TreeError(f"{name!r} is nested under the file {stack[-1][1]!r}")
        prefix = "".join(n for _, n in stack)
        paths.append(prefix + name)
        stack.append((col, name))
    roots = [p for p in paths if "/" not in p.rstrip("/")]
    if len(roots) == 1 and roots[0].endswith("/") and len(paths) > 1:
        root = roots[0]
        paths = [p[len(root) :] for p in paths if p != root]
    return set(paths)


def strip_dot(path: str) -> str:
    while path.startswith("./"):
        path = path[2:]
    return path


def contains(tree: set[str], path: str) -> bool:
    """True when ``path`` is declared or lies inside a declared directory."""
    path = strip_dot(path)
    return any(path in (p, p.rstrip("/")) or (p.endswith("/") and path.startswith(p)) for p in tree)
