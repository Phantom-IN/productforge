"""Observe-mode redaction — applied before anything touches disk.

Stdlib only and pure: the recorder (Playwright venv) and ``pflib`` both import it. Rules:

- headers: an allowlist of harmless names survives; ``Authorization``, ``Cookie``, ``Set-Cookie``,
  API keys and everything else are dropped
- URLs: no user:password, no fragment; query values become their type; id-, e-mail- and
  token-like path segments become ``:id`` · ``:email`` · ``:token``
- bodies: JSON becomes a field shape (``{"title": "string", "due": "date|null"}``); arrays collapse
  to one element shape; object keys that are data (IDs, e-mails) collapse to ``<id>`` ·
  ``<email>``; GraphQL keeps the operation type, name and top-level fields — never the query text
  or variable values; form bodies keep their keys; anything else becomes its kind and size
- free text (console errors, dialog messages): URLs redacted, quoted strings, e-mails, IP
  addresses, long numbers and token-like runs masked
- events: a ``value`` becomes ``value_shape`` (type + length bucket); names of repeated items
  (list rows, table cells — task titles, people) become ``<item>``; labels and URLs redacted
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qsl, unquote, urlsplit, urlunsplit

SAFE_HEADERS = frozenset({
    "accept", "accept-language", "access-control-allow-methods", "access-control-allow-origin",
    "cache-control", "content-encoding", "content-length", "content-security-policy",
    "content-type", "location", "referer", "retry-after", "vary", "x-frame-options",
    "x-requested-with",
})  # fmt: skip
URL_HEADERS = frozenset({"location", "referer"})
SHAPE_KEYS = frozenset({"request_shape", "response_shape", "shape"})
URL_KEYS = frozenset({"url", "href", "frame_url"})
LABEL_KEYS = frozenset({"name", "title", "label"})
TEXT_KEYS = frozenset({"message", "text"})
VALUE_KEYS = frozenset({"value", "values", "password", "input_value"})
MAX_LABEL = 80
MAX_TEXT = 200
MAX_DEPTH = 8
MAX_KEYS = 200

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
_HEXID = re.compile(r"^[0-9a-f]{12,}$", re.I)
_MIXED_ID = re.compile(r"^(?=.*\d)[A-Za-z0-9_-]{16,}$")
_JWT = re.compile(r"eyJ[\w-]{4,}\.[\w-]{4,}\.[\w-]*")
_TOKEN_SEGMENT = re.compile(r"^[A-Za-z0-9_\-+/=.~]{24,}$")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_LONG_NUMBER = re.compile(r"\d{6,}")
_TOKENISH = re.compile(r"(?=[A-Za-z0-9_\-+/=.]*\d)[A-Za-z0-9_\-+/=.]{24,}")  # with a digit
_URL_IN_TEXT = re.compile(r"\b(?:https?|wss?)://[^\s\"'<>)]+")
_QUOTED = re.compile(r"\"[^\"\n]{1,200}\"|'[^'\n]{1,200}'|“[^”\n]{1,200}”|‘[^’\n]{1,200}’")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ][\d:.]+(Z|[+-]\d{2}:?\d{2})?)?$")
_NUMBER = re.compile(r"^-?\d+(\.\d+)?$")
_SLUG = re.compile(r"^(?:[a-z]+|\d{1,4})(?:[-_.](?:[a-z]+|\d{1,4}))+$")  # 2026-release-notes


def headers(h: dict[str, str] | None) -> dict[str, str]:
    """Keep only allowlisted headers (lower-cased names); URL-valued ones are redacted too."""
    out: dict[str, str] = {}
    for name, value in (h or {}).items():
        key = name.lower()
        if key in SAFE_HEADERS:
            out[key] = url(value) if key in URL_HEADERS else value[:MAX_TEXT]
    return out


def data_key(k: str) -> str | None:
    """The placeholder for a key or segment that is data rather than structure, else None."""
    k = unquote(k)
    if _EMAIL.fullmatch(k):
        return "email"
    if _JWT.fullmatch(k):
        return "token"
    if _SLUG.match(k):
        return None
    if k.isdigit() or _UUID.match(k) or _HEXID.match(k) or _MIXED_ID.match(k):
        return "id"
    if _TOKEN_SEGMENT.match(k) and _TOKENISH.fullmatch(k):
        return "token"
    return None


def segment(part: str) -> str:
    kind = data_key(part) if part else None
    return f":{kind}" if kind else part


def url(u: str) -> str:
    """``https://u:p@h/p/123?token=abc#x`` → ``https://h/p/:id?token=string``."""
    parts = urlsplit(u)
    host = parts.hostname or ""
    netloc = host + (f":{parts.port}" if parts.port else "") if parts.netloc else ""
    path = "/".join(segment(p) for p in parts.path.split("/"))
    query = "&".join(
        f"{segment(k) if data_key(k) else k}={scalar_type(v)}"
        for k, v in parse_qsl(parts.query, True)
    )
    return urlunsplit((parts.scheme, netloc, path, query, ""))


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
        if _NUMBER.match(v):
            return "number"
        if v in ("true", "false"):
            return "bool"
        return "string"
    return type(v).__name__


def shape(v: Any, depth: int = 0) -> Any:
    """A JSON value's field shape: leaves become their type, arrays collapse to one element,
    keys that are data (IDs, e-mails) collapse into one ``<id>`` / ``<email>`` key."""
    if depth >= MAX_DEPTH:
        return "…"
    if isinstance(v, dict):
        grouped: dict[str, list[Any]] = {}
        for k, x in list(v.items())[:MAX_KEYS]:
            kind = data_key(str(k))
            grouped.setdefault(f"<{kind}>" if kind else str(k), []).append(shape(x, depth + 1))
        out = {k: merge_shapes(xs) for k, xs in sorted(grouped.items())}
        if len(v) > MAX_KEYS:
            out["…"] = f"{len(v) - MAX_KEYS} more keys"
        return out
    if isinstance(v, list):
        if not v:
            return []
        return [merge_shapes([shape(x, depth + 1) for x in v[:MAX_KEYS]])]
    return scalar_type(v)


def merge_shapes(shapes: list[Any]) -> Any:
    """Combine element shapes: dict keys union; differing leaves joined (``string|null``)."""
    if len(shapes) == 1:
        return shapes[0]
    if all(isinstance(s, dict) for s in shapes):
        keys = sorted({k for s in shapes for k in s})
        return {k: merge_shapes([s[k] for s in shapes if k in s]) for k in keys}
    if all(isinstance(s, list) for s in shapes):
        inner = [s[0] for s in shapes if s]
        return [merge_shapes(inner)] if inner else []
    if all(isinstance(s, str) for s in shapes):
        return "|".join(sorted({p for s in shapes for p in s.split("|")}))
    seen: list[str] = []
    for s in shapes:
        key = json.dumps(s, sort_keys=True)
        if key not in seen:
            seen.append(key)
    return json.loads(seen[0]) if len(seen) == 1 else "mixed"


# -- GraphQL -------------------------------------------------------------------------------------
_GQL_STRING = re.compile(r'"""[\s\S]*?"""|"(?:\\.|[^"\\])*"')
_GQL_COMMENT = re.compile(r"#[^\n]*")
_GQL_OP = re.compile(r"^\s*(query|mutation|subscription)\b\s*([_A-Za-z][_0-9A-Za-z]*)?")
_GQL_NAME = re.compile(r"[_A-Za-z][_0-9A-Za-z]*")


def graphql_fields(query: str) -> list[str]:
    """Top-level selection field names of the first operation (aliases resolved), no arguments."""
    q = _GQL_COMMENT.sub("", _GQL_STRING.sub('""', query))
    start = q.find("{")
    fields: list[str] = []
    depth = parens = 0
    i = start
    while 0 <= i < len(q):
        c = q[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                break
        elif c == "(":
            parens += 1
        elif c == ")":
            parens -= 1
        elif depth == 1 and parens == 0 and (m := _GQL_NAME.match(q, i)):
            name = m.group(0)
            rest = q[m.end() :].lstrip()
            if rest.startswith(":"):  # alias: the real field follows
                i = m.end()
                continue
            before = q[:i].rstrip()
            after_on = before.endswith(" on") and before[:-3].rstrip().endswith("...")
            if name != "on" and not before.endswith("...") and not after_on:
                fields.append(name)  # (fragment spreads and `... on Type` conditions are not)
            i = m.end()
            continue
        i += 1
    return list(dict.fromkeys(fields))


def graphql(op: dict[str, Any]) -> dict[str, Any] | None:
    """One GraphQL request → ``{"graphql": {operation, name, fields}, "variables": shape}``."""
    query = op.get("query")
    persisted = isinstance(op.get("extensions"), dict) and "persistedQuery" in op["extensions"]
    if not isinstance(query, str) and not persisted:
        return None
    info: dict[str, Any] = {}
    if isinstance(query, str):
        m = _GQL_OP.match(_GQL_COMMENT.sub("", query))
        info["operation"] = m.group(1) if m else "query"
        if m and m.group(2):
            info["name"] = m.group(2)
        info["fields"] = graphql_fields(query)
    else:
        info["persisted"] = True
    if isinstance(op.get("operationName"), str):
        info["name"] = op["operationName"]
    out: dict[str, Any] = {"graphql": info}
    if isinstance(op.get("variables"), dict):
        out["variables"] = shape(op["variables"])
    return out


def _graphql_body(data: Any) -> Any:
    if isinstance(data, dict):
        return graphql(data)
    if isinstance(data, list) and data and all(isinstance(x, dict) for x in data):
        ops = [graphql(x) for x in data]
        return ops if all(o is not None for o in ops) else None
    return None


def body(content_type: str | None, text: str | bytes | None) -> Any:
    """A request/response body reduced to its shape (never its values)."""
    if text is None or text == b"" or text == "":
        return None
    kind = (content_type or "").split(";")[0].strip().lower()
    raw = text.decode("utf-8", "replace") if isinstance(text, bytes) else text
    if "json" in kind or (not kind and raw.lstrip()[:1] in ("[", "{")):
        try:
            data = json.loads(raw)
        except ValueError:
            pass
        else:
            gql = _graphql_body(data)
            return gql if gql is not None else shape(data)
    if kind == "application/x-www-form-urlencoded":
        return {segment(k) if data_key(k) else k: scalar_type(v) for k, v in parse_qsl(raw, True)}
    if kind == "application/graphql":
        return graphql({"query": raw})
    return {"kind": kind or "text", "bytes": size_bucket(len(raw))}


def size_bucket(n: int) -> str:
    for limit, label in ((0, "0"), (100, "<100"), (1_000, "<1k"), (10_000, "<10k"),
                         (100_000, "<100k"), (1_000_000, "<1M")):  # fmt: skip
        if n <= limit:
            return label
    return ">=1M"


def text(t: str | None) -> str:
    """Free text with URLs redacted and quoted strings, e-mails, IPs, long numbers and token-like
    runs masked, cut to MAX_TEXT."""
    if not t:
        return ""
    pieces, last = [], 0
    for m in _URL_IN_TEXT.finditer(t):  # URLs get url(); only the text between them is masked
        pieces += [_mask(t[last : m.start()]), url(m.group(0))]
        last = m.end()
    pieces.append(_mask(t[last:]))
    return "".join(pieces)[:MAX_TEXT]


def _mask(s: str) -> str:
    s = _QUOTED.sub("<text>", s)
    s = _EMAIL.sub("<email>", s)
    s = _JWT.sub("<token>", s)
    s = _IPV4.sub("<ip>", s)
    s = _TOKENISH.sub("<token>", s)
    return _LONG_NUMBER.sub("<number>", s)


def label(t: str | None) -> str:
    """A UI label (accessible name, heading): whitespace collapsed, masked, cut to MAX_LABEL."""
    t = " ".join((t or "").split())
    t = _EMAIL.sub("<email>", t)
    t = _JWT.sub("<token>", t)
    t = _TOKENISH.sub("<token>", t)
    t = _LONG_NUMBER.sub("<number>", t)
    return t[:MAX_LABEL]


def value_shape(v: Any) -> dict[str, str]:
    return {"type": scalar_type(v), "length": size_bucket(len(str(v)) if v is not None else 0)}


def event(e: dict[str, Any]) -> dict[str, Any]:
    """The last gate before disk: values become shapes, item names become ``<item>``, labels,
    texts and URLs are redacted — recursively."""
    out: dict[str, Any] = {}
    item = bool(e.get("in_item")) and not e.get("in_nav")
    for k, v in e.items():
        if k in VALUE_KEYS:
            out["value_shape"] = value_shape(v)
        elif k in SHAPE_KEYS:
            out[k] = v
        elif k in URL_KEYS and isinstance(v, str):
            out[k] = url(v)
        elif k in LABEL_KEYS and isinstance(v, str):
            out[k] = "<item>" if item and v else label(v)
        elif k in TEXT_KEYS and isinstance(v, str):
            out[k] = text(v)
        elif isinstance(v, dict):
            out[k] = event(v)
        elif isinstance(v, list):
            out[k] = [event(x) if isinstance(x, dict) else _scalar_in_list(k, x) for x in v]
        else:
            out[k] = v
    return out


def collapse(items: list[Any]) -> list[Any]:
    """Identical entries (``<item>`` links to ``/tasks/:id``) become one with a ``count``."""
    out: list[Any] = []
    index: dict[str, int] = {}
    for x in items:
        key = json.dumps(x, sort_keys=True)
        if key in index:
            if isinstance(out[index[key]], dict):
                out[index[key]]["count"] = out[index[key]].get("count", 1) + 1
        else:
            index[key] = len(out)
            out.append(dict(x) if isinstance(x, dict) else x)
    return out


def _scalar_in_list(key: str, x: Any) -> Any:
    return label(x) if isinstance(x, str) else x
