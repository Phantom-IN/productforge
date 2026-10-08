from __future__ import annotations

import re
from pathlib import Path

import pytest

from pflib import taxonomy, urls

REF = Path(__file__).resolve().parents[2] / "skills/productforge/references/source-tiers.md"


@pytest.mark.parametrize(
    "raw, canonical",
    [
        ("HTTPS://Docs.Tasklet.Example/Guide/", "https://docs.tasklet.example/Guide"),
        ("https://tasklet.example", "https://tasklet.example/"),
        ("https://tasklet.example:443/a#section", "https://tasklet.example/a"),
        ("http://tasklet.example:8080/a", "http://tasklet.example:8080/a"),
        ("https://x.example/a?utm_source=m&b=2&a=1&gclid=z", "https://x.example/a?a=1&b=2"),
        ("https://x.example/docs/index.html", "https://x.example/docs"),
        ("https://x.example/a?ref=hn", "https://x.example/a"),
    ],
)
def test_canonicalize(raw: str, canonical: str) -> None:
    assert urls.canonicalize(raw) == canonical
    assert urls.canonicalize(canonical) == canonical  # idempotent


@pytest.mark.parametrize(
    "host, domain",
    [
        ("docs.tasklet.example", "tasklet.example"),
        ("tasklet.example", "tasklet.example"),
        ("a.b.example.co.uk", "example.co.uk"),
        ("localhost", "localhost"),
    ],
)
def test_registrable_domain(host: str, domain: str) -> None:
    assert urls.registrable_domain(host) == domain


def test_same_site() -> None:
    assert urls.same_site("https://docs.tasklet.example/a", "https://tasklet.example/b")
    assert not urls.same_site("https://community.example/t", "https://social.example/p")


def test_taxonomy_is_consistent() -> None:
    assert len(taxonomy.BY_NAME) == len(taxonomy.CATEGORIES)
    assert all(c.tier in taxonomy.TIERS for c in taxonomy.CATEGORIES)
    assert all(c.official == (c.name in taxonomy.OFFICIAL) for c in taxonomy.CATEGORIES)
    assert taxonomy.default_tier("docs") == 1 and taxonomy.default_tier("nope") is None


def test_reference_lists_every_category_with_its_tier() -> None:
    text = REF.read_text(encoding="utf-8")
    rows = dict(re.findall(r"^\| `([a-z-]+)` \| (\d) \|", text, re.M))
    assert rows == {c.name: str(c.tier) for c in taxonomy.CATEGORIES}
