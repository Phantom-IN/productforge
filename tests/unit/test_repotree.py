from __future__ import annotations

import pytest

from pflib import repotree

GLYPHS = """\
tasklet-alt/
├── apps/
│   ├── web/          # Next.js UI
│   └── api/
├── packages/
│   └── db/
├── README.md
└── tests/
"""


def test_box_drawing_tree_drops_the_root() -> None:
    assert repotree.parse(GLYPHS) == {
        "apps/", "apps/web/", "apps/api/", "packages/", "packages/db/", "README.md", "tests/",
    }  # fmt: skip


def test_indented_tree_without_a_root() -> None:
    assert repotree.parse("apps/\n  web/\n  api/\ntests/\n") == {
        "apps/", "apps/web/", "apps/api/", "tests/",
    }  # fmt: skip


def test_contains() -> None:
    tree = repotree.parse(GLYPHS)
    assert repotree.contains(tree, "apps/api/src/tasks.ts")
    assert repotree.contains(tree, "./README.md")
    assert not repotree.contains(tree, "lib/tasks.ts")
    assert not repotree.contains(tree, "README.md.bak")


@pytest.mark.parametrize(
    "text, message",
    [("", "empty"), ("apps/\n  my web app/\n", "not a path"),
     ("README.md\n  nested/\n", "nested under the file")],
)  # fmt: skip
def test_bad_trees(text: str, message: str) -> None:
    with pytest.raises(repotree.TreeError, match=message):
        repotree.parse(text)


def test_fenced_block() -> None:
    assert repotree.fenced_block("x\n```text\napps/\n```\n") == "apps/\n"
    assert repotree.fenced_block("no fence") is None
