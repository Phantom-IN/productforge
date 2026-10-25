"""URL canonicalisation and site identity.

Pure functions, no network. ``canonicalize`` is the dedupe key for sources;
``registrable_domain`` decides whether two sources are "distinct hosts" for PROBABLE.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Common multi-label public suffixes (the stdlib has no public-suffix list).
MULTI_PART_TLDS = frozenset(
    {
        "co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au", "co.nz",
        "co.jp", "co.in", "co.kr", "com.br", "com.cn", "com.mx", "com.sg", "co.za",
    }
)  # fmt: skip

TRACKING_PARAMS = frozenset({"ref", "gclid", "fbclid", "mc_cid", "mc_eid", "msclkid", "_ga"})
DEFAULT_PORTS = {"http": 80, "https": 443}


def _is_tracking(key: str) -> bool:
    return key.lower().startswith("utm_") or key.lower() in TRACKING_PARAMS


def canonicalize(url: str) -> str:
    """Canonical form of a URL for deduplication.

    Lowercases scheme and host, drops default ports, fragments and tracking parameters
    (``utm_*``, ``gclid``, …), sorts the remaining query parameters, removes a trailing
    ``index.html`` and the trailing slash (except for the root path).
    """
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    port = parts.port
    netloc = host if port in (None, DEFAULT_PORTS.get(scheme)) else f"{host}:{port}"
    path = parts.path or "/"
    if path.endswith("/index.html"):
        path = path[: -len("index.html")]
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/") or "/"
    query = urlencode(
        sorted(
            (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _is_tracking(k)
        )
    )
    return urlunsplit((scheme, netloc, path, query, ""))


def page_key(url: str) -> str:
    """Comparison key: the canonical URL with a leading ``www.`` removed from the host.

    ``www.host`` and ``host`` serve the same page; use this only to compare, never to store.
    """
    parts = urlsplit(canonicalize(url))
    host = parts.netloc
    if host.startswith("www."):
        host = host[len("www.") :]
    return urlunsplit((parts.scheme, host, parts.path, parts.query, ""))


def host_of(url: str) -> str:
    return (urlsplit(url.strip()).hostname or "").lower()


def registrable_domain(host: str) -> str:
    """``docs.tasklet.example`` → ``tasklet.example``; ``a.b.co.uk`` → ``b.co.uk``."""
    labels = [label for label in host.lower().strip(".").split(".") if label]
    if len(labels) >= 3 and ".".join(labels[-2:]) in MULTI_PART_TLDS:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def same_site(a: str, b: str) -> bool:
    """True when two URLs belong to the same registrable domain."""
    return registrable_domain(host_of(a)) == registrable_domain(host_of(b))


_WORD = re.compile(r"[a-z]+")
_SIBILANT_ES = re.compile(r"(s|x|z|ch|sh)es$")
MIN_TOKEN = 4


def stem(word: str) -> str:
    """Lightly stem a lowercase word: strip ``ing``/``ed``/``es``/``s``, keeping 4+ letters.

    ``es`` is stripped only after a sibilant (``classes`` -> ``class``); otherwise a plural is
    just ``s`` (``cases`` -> ``case``).
    """
    for suffix in ("ing", "ed"):
        if word.endswith(suffix) and len(word) - len(suffix) >= MIN_TOKEN:
            return word[: -len(suffix)]
    if _SIBILANT_ES.search(word) and len(word) - 2 >= MIN_TOKEN:
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) - 1 >= MIN_TOKEN:
        return word[:-1]
    return word


def tokens(text: str) -> set[str]:
    """Lowercase stemmed words of ``text`` with at least ``MIN_TOKEN`` letters."""
    return {s for w in _WORD.findall(text.lower()) if len(s := stem(w)) >= MIN_TOKEN}


def slug_tokens(url: str) -> set[str]:
    """Stemmed words of a URL's path (slugs split on any non-letter)."""
    return tokens(urlsplit(url).path)
