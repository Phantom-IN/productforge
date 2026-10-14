"""Observe-mode redaction (IMPLEMENTATION_PLAN.md §23.4) — applied before anything touches disk.

Stdlib only and pure: the recorder (Playwright venv) and ``pflib`` both import it. Rules:

- headers: an allowlist of harmless names survives; ``Authorization``, ``Cookie``, ``Set-Cookie``
  and everything else are dropped
- URLs: query values become their type, id-like path segments become ``:id``, no fragment
- bodies: JSON becomes a field shape (``{"title": "string", "due": "date|null"}``); arrays collapse
  to one element shape; form bodies keep their keys; anything else becomes its kind and size
- free text (console errors, dialog messages): e-mails, long numbers and token-like runs masked
- events: never carry a ``value``; long labels are cut
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

SAFE_HEADERS = frozenset({
    "accept", "accept-language", "access-control-allow-methods", "access-control-allow-origin",
    "cache-control", "content-encoding", "content-length", "content-security-policy",
    "content-type", "location", "referer", "retry-after", "vary", "x-frame-options",
    "x-requested-with",
})  # fmt: skip
URL_HEADERS = frozenset({"location", "referer"})
MAX_LABEL = 80
MAX_TEXT = 200
MAX_DEPTH = 8

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
_HEXID = re.compile(r"^[0-9a-f]{12,}$", re.I)
_MIXED_ID = re.compile(r"^(?=.*\d)[A-Za-z0-9_-]{16,}$")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_LONG_NUMBER = re.compile(r"\d{6,}")
_TOKENISH = re.compile(r"[A-Za-z0-9_\-+/=.]{24,}")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ][\d:.]+(Z|[+-]\d{2}:?\d{2})?)?$")


def headers(h: dict[str, str] | None) -> dict[str, str]:
    """Keep only allowlisted headers (lower-cased names); URL-valued ones are redacted too."""
    out: dict[str, str] = {}
    for name, value in (h or {}).items():
        key = name.lower()
        if key in SAFE_HEADERS:
            out[key] = url(value) if key in URL_HEADERS else value[:MAX_TEXT]
    return out


def segment(part: str) -> str:
    if part.isdigit() or _UUID.match(part) or _HEXID.match(part) or _MIXED_ID.match(part):
        return ":id"
    if _EMAIL.fullmatch(part):
        return ":email"
    return part


def url(u: str) -> str:
    """``https://h/p/123?token=abc#x`` → ``https://h/p/:id?token=string``."""
    parts = urlsplit(u)
    path = "/".join(segment(p) for p in parts.path.split("/"))
    query = "&".join(f"{k}={scalar_type(v)}" for k, v in parse_qsl(parts.query, True))
    return urlunsplit((parts.scheme, parts.netloc, path, query, ""))


def route(u: str) -> str:
    """The path template only: ``https://h/p/123?x=1`` → ``/p/:id``."""
    return urlsplit(url(u)).path or "/"


def scalar_type(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int | float):
        return "number"
    if isinstance(v, str):
        if _DATE.match(v):
            return "date"
        if v.lstrip("-").replace(".", "", 1).isdigit():
            return "number"
        return "string"
    return type(v).__name__


def shape(v: Any, depth: int = 0) -> Any:
    """A JSON value's field shape: leaves become their type, arrays collapse to one element."""
    if depth >= MAX_DEPTH:
        return "…"
    if isinstance(v, dict):
        return {str(k): shape(x, depth + 1) for k, x in sorted(v.items())}
    if isinstance(v, list):
        if not v:
            return []
        shapes = [shape(x, depth + 1) for x in v]
        return [merge_shapes(shapes)]
    return scalar_type(v)


def merge_shapes(shapes: list[Any]) -> Any:
    """Combine element shapes: dict keys union; differing leaves joined (``string|null``)."""
    if all(isinstance(s, dict) for s in shapes):
        keys = sorted({k for s in shapes for k in s})
        return {k: merge_shapes([s[k] for s in shapes if k in s]) for k in keys}
    leaves = []
    for s in shapes:
        key = json.dumps(s, sort_keys=True)
        if key not in leaves:
            leaves.append(key)
    if len(leaves) == 1:
        return shapes[0]
    if all(isinstance(s, str) for s in shapes):
        return "|".join(sorted({p for s in shapes for p in s.split("|")}))
    return shapes[0]


def body(content_type: str | None, text: str | bytes | None) -> Any:
    """A request/response body reduced to its shape (never its values)."""
    if text is None or text == b"" or text == "":
        return None
    kind = (content_type or "").split(";")[0].strip().lower()
    raw = text.decode("utf-8", "replace") if isinstance(text, bytes) else text
    if "json" in kind or (not kind and raw[:1] in "[{"):
        try:
            return shape(json.loads(raw))
        except ValueError:
            pass
    if kind == "application/x-www-form-urlencoded":
        return {k: scalar_type(v) for k, v in parse_qsl(raw, True)}
    return {"kind": kind or "unknown", "bytes": size_bucket(len(raw))}


def size_bucket(n: int) -> str:
    for limit, label in ((0, "0"), (100, "<100"), (1_000, "<1k"), (10_000, "<10k"),
                         (100_000, "<100k"), (1_000_000, "<1M")):  # fmt: skip
        if n <= limit:
            return label
    return ">=1M"


def text(t: str | None) -> str:
    """Free text with e-mails, long numbers and token-like runs masked, cut to MAX_TEXT."""
    if not t:
        return ""
    t = _EMAIL.sub("<email>", t)
    t = _TOKENISH.sub("<token>", t)
    t = _LONG_NUMBER.sub("<number>", t)
    return t[:MAX_TEXT]


def label(t: str | None) -> str:
    """A UI label (accessible name, heading): whitespace collapsed, masked, cut to MAX_LABEL."""
    return text(" ".join((t or "").split()))[:MAX_LABEL]


def event(e: dict[str, Any]) -> dict[str, Any]:
    """The last gate before ``events.jsonl``: no ``value`` keys, labels and URLs redacted."""
    out: dict[str, Any] = {}
    for k, v in e.items():
        if k in ("value", "values", "password"):
            continue
        if k in ("url", "href", "frame_url") and isinstance(v, str):
            out[k] = url(v)
        elif k in ("name", "title", "label") and isinstance(v, str):
            out[k] = label(v)
        elif k in ("message", "text") and isinstance(v, str):
            out[k] = text(v)
        elif isinstance(v, dict) and k not in ("request_shape", "response_shape", "shape"):
            out[k] = event(v)
        elif isinstance(v, list) and k not in ("request_shape", "response_shape", "shape"):
            out[k] = [event(x) if isinstance(x, dict) else x for x in v]
        else:
            out[k] = v
    return out
