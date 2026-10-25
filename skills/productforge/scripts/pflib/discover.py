"""Reconnaissance — the ONLY networked ProductForge module.

``discover(root_url)`` finds candidate source URLs without reading page content:

- fetches ``robots.txt`` for every host it touches and **never** requests a disallowed URL
  (redirects are followed manually, only within the target's site and only when allowed);
- reads ``sitemap.xml`` / sitemap indexes (gzip supported, bounded);
- collects links from the homepage (off-site links are recorded, never fetched);
- probes common subdomains (``docs.``, ``help.``, ``developers.``, ``status.`` …);
- classifies every URL into a source category and ranks candidates per host before capping:
  homepage-navigation links, then scope relevance, then category priority, then depth. Without
  scope terms the cap falls back to round-robin across categories.

Agents then read only ``allowed: true`` URLs. Every request waits ``research.request_delay_seconds``
and sends ``research.user_agent``.
"""

from __future__ import annotations

import gzip
import json
import time
import urllib.error
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

from pflib import discover_rules, taxonomy, urls, workspace
from pflib.io import atomic_write_text

TIMEOUT_SECONDS = 10
MAX_BYTES = 5_000_000
MAX_SITEMAP_FILES_PER_HOST = 10
MAX_LOCS_PER_HOST = 5000
MAX_REDIRECTS = 3
MAX_HOSTS = 12


@dataclass
class Response:
    url: str
    status: int  # 0 = no response (DNS, connection, timeout)
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None  # surface 3xx as HTTPError; ProductForge decides whether to follow


class Fetcher:
    """Polite HTTP client. ``host_map`` routes hostnames to ``ip:port`` (tests; no DNS)."""

    def __init__(
        self,
        user_agent: str,
        delay: float,
        host_map: dict[str, str] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.user_agent = user_agent
        self.delay = delay
        self.host_map = host_map
        self.sleep = sleep
        self.requests: list[tuple[str, str]] = []
        self._opener = urllib.request.build_opener(_NoRedirect)

    def fetch(self, url: str, method: str = "GET") -> Response:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        target = url
        headers = {"User-Agent": self.user_agent, "Accept-Encoding": "gzip"}
        if self.host_map is not None:
            if host not in self.host_map:
                return Response(url, 0, error=f"unresolvable host {host} (host map)")
            target = urlunsplit((parts.scheme, self.host_map[host], parts.path or "/",
                                 parts.query, ""))  # fmt: skip
            headers["Host"] = parts.netloc
        if self.requests and self.delay > 0:
            self.sleep(self.delay)
        self.requests.append((method, url))
        req = urllib.request.Request(target, method=method, headers=headers)
        try:
            with self._opener.open(req, timeout=TIMEOUT_SECONDS) as resp:
                return self._response(url, resp.status, dict(resp.headers), resp.read(MAX_BYTES))
        except urllib.error.HTTPError as exc:
            body = exc.read(MAX_BYTES) if exc.fp else b""
            return self._response(url, exc.code, dict(exc.headers or {}), body)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            return Response(url, 0, error=f"{type(exc).__name__}: {exc}")

    @staticmethod
    def _response(url: str, status: int, headers: dict[str, str], body: bytes) -> Response:
        lower = {k.lower(): v for k, v in headers.items()}
        if lower.get("content-encoding") == "gzip" or (body[:2] == b"\x1f\x8b"):
            try:
                body = gzip.decompress(body)[:MAX_BYTES]
            except OSError:
                pass
        return Response(url, status, lower, body)


class Robots:
    """robots.txt per host: 2xx → parsed; 401/403 → everything disallowed; else allowed."""

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher
        self._cache: dict[
            str, tuple[urllib.robotparser.RobotFileParser | bool, list[str], Response]
        ] = {}

    def load(self, scheme: str, host: str) -> Response:
        key = f"{scheme}://{host}"
        if key not in self._cache:
            resp = self.fetcher.fetch(f"{key}/robots.txt")
            sitemaps: list[str] = []
            rules: urllib.robotparser.RobotFileParser | bool
            if resp.ok:
                parser = urllib.robotparser.RobotFileParser()
                parser.parse(resp.text().splitlines())
                rules, sitemaps = parser, list(parser.site_maps() or [])
            elif resp.status in (401, 403):
                rules = False
            else:
                rules = True
            self._cache[key] = (rules, sitemaps, resp)
        return self._cache[key][2]

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        self.load(parts.scheme, (parts.netloc or "").lower())
        rules = self._cache[f"{parts.scheme}://{(parts.netloc or '').lower()}"][0]
        if isinstance(rules, bool):
            return rules
        return rules.can_fetch(self.fetcher.user_agent, url)

    def sitemaps(self, scheme: str, host: str) -> list[str]:
        self.load(scheme, host)
        return self._cache[f"{scheme}://{host}"][1]


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href.strip())


@dataclass
class DiscoverResult:
    root: str
    host: str
    domain: str
    fetched_at: str
    entries: list[dict[str, Any]] = field(default_factory=list)
    external: list[dict[str, Any]] = field(default_factory=list)
    probes: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    requests: int = 0
    disallowed: int = 0
    truncated: int = 0

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for entry in self.entries:
            key = entry["category"] or "unclassified"
            out[key] = out.get(key, 0) + 1
        return dict(sorted(out.items()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "host": self.host,
            "domain": self.domain,
            "fetched_at": self.fetched_at,
            "counts": self.counts(),
            "disallowed": self.disallowed,
            "truncated": self.truncated,
            "requests": self.requests,
            "probes": self.probes,
            "errors": self.errors,
            "entries": self.entries,
            "external": self.external,
        }


def _follow(fetcher: Fetcher, robots: Robots, url: str, domain: str) -> Response:
    """GET with manual redirects: only within ``domain`` and only to allowed URLs."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        resp = fetcher.fetch(current)
        if resp.status not in (301, 302, 303, 307, 308):
            return resp
        location = resp.headers.get("location")
        if not location:
            return resp
        nxt = urljoin(current, location)
        host = (urlsplit(nxt).hostname or "").lower()
        if urls.registrable_domain(host) != domain or not robots.allowed(nxt):
            resp.error = f"redirect to {nxt} not followed (off-site or disallowed)"
            return resp
        current = nxt
    return Response(url, 0, error="too many redirects")


def _sitemap_locs(fetcher: Fetcher, robots: Robots, scheme: str, host: str, domain: str,
                  errors: list[dict[str, Any]]) -> list[str]:  # fmt: skip
    queue = list(dict.fromkeys(robots.sitemaps(scheme, host) + [f"{scheme}://{host}/sitemap.xml"]))
    seen: set[str] = set()
    locs: list[str] = []
    while queue and len(seen) < MAX_SITEMAP_FILES_PER_HOST and len(locs) < MAX_LOCS_PER_HOST:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        if urls.registrable_domain((urlsplit(sm).hostname or "").lower()) != domain:
            continue
        if not robots.allowed(sm):
            continue
        resp = _follow(fetcher, robots, sm, domain)
        if not resp.ok:
            if resp.status != 404:
                errors.append({"url": sm, "status": resp.status, "error": resp.error})
            continue
        try:
            root = ET.fromstring(resp.body)
        except ET.ParseError as exc:
            errors.append({"url": sm, "status": resp.status, "error": f"bad sitemap XML: {exc}"})
            continue
        kind = root.tag.rsplit("}", 1)[-1]
        found = [
            el.text.strip() for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "loc" and el.text
        ]
        if kind == "sitemapindex":
            queue.extend(found)
        else:
            locs.extend(found)
    return locs[:MAX_LOCS_PER_HOST]


def _probe_paths(
    fetcher: Fetcher,
    robots: Robots,
    scheme: str,
    host: str,
    domain: str,
    known: dict[str, dict[str, Any]],
    add: Callable[[str, str], None],
) -> None:
    """HEAD well-known official paths that sitemaps/homepage did not list (robots-checked)."""
    covered = {discover_rules.classify(url, domain) for url in known}
    for path in discover_rules.WELL_KNOWN_PATHS:
        url = f"{scheme}://{host}{path}"
        if urls.canonicalize(url) in known or discover_rules.classify(url, domain) in covered:
            continue
        if not robots.allowed(url):
            continue
        resp = fetcher.fetch(url, method="HEAD")
        if resp.status == 405:
            resp = fetcher.fetch(url)
        if 200 <= resp.status < 300:
            add(url, "path-probe")
        elif resp.status in (301, 302, 303, 307, 308) and resp.headers.get("location"):
            target = urljoin(url, resp.headers["location"])
            target_host = (urlsplit(target).hostname or "").lower()
            if urls.registrable_domain(target_host) == domain and robots.allowed(target):
                add(target, "path-probe")


# Category order for ranking (best first): pages that describe the product come before long tails.
CATEGORY_PRIORITY: tuple[str, ...] = (
    "homepage", "features", "enterprise", "pricing", "integrations", "docs", "api-docs",
    "security", "changelog", "help-center", "official-tutorial", "official-demo", "product-blog",
    "engineering-blog", "official-talk", "official-repo", "status", "company",
)  # fmt: skip


def _priority(category: str | None) -> int:
    if category in CATEGORY_PRIORITY:
        return CATEGORY_PRIORITY.index(str(category))
    if category in taxonomy.BY_NAME:
        return len(CATEGORY_PRIORITY)
    return len(CATEGORY_PRIORITY) + 1  # unclassified


def _depth(entry: dict[str, Any]) -> int:
    return int(urlsplit(entry["url"]).path.count("/"))


def _annotate(entries: list[dict[str, Any]], terms: set[str]) -> None:
    for e in entries:
        e["scope_hits"] = len(urls.slug_tokens(e["canonical_url"]) & terms) if terms else 0
        e["nav"] = bool(e.get("nav"))


def _finish(kept: list[dict[str, Any]], total: int) -> tuple[list[dict[str, Any]], int]:
    for rank, e in enumerate(kept, 1):
        e["rank"] = rank
    return kept, total - len(kept)


def _cap_ranked(
    entries: list[dict[str, Any]], cap: int, terms: Iterable[str] = ()
) -> tuple[list[dict[str, Any]], int]:
    """Keep at most ``cap`` entries, best first, and store ``rank`` / ``scope_hits`` / ``nav``.

    With scope terms: sort by (company page last, homepage-navigation link, scope hits, category
    priority, depth, URL). Without terms: navigation links first, then round-robin across
    categories.
    """
    terms = set(terms)
    cap = max(0, cap)
    _annotate(entries, terms)
    if terms:
        ordered = sorted(
            entries,
            key=lambda e: (
                e["category"] == "company",  # navigation never lifts a company page
                not e["nav"], -e["scope_hits"], _priority(e["category"]), _depth(e), e["url"],
            ),
        )  # fmt: skip
        return _finish(ordered[:cap], len(entries))
    return _finish(*_round_robin(entries, cap))


def _round_robin(entries: list[dict[str, Any]], cap: int) -> tuple[list[dict[str, Any]], int]:
    """One entry per category in turn; within a category navigation links, then shallow URLs."""
    buckets: dict[str, list[dict[str, Any]]] = {}
    for e in sorted(entries, key=lambda e: (not e["nav"], _depth(e), e["url"])):
        name = "~company" if e["category"] == "company" else e["category"] or "~unclassified"
        buckets.setdefault(name, []).append(e)  # company pages are never researched: last
    order = sorted(buckets)
    kept: list[dict[str, Any]] = []
    while len(kept) < cap:
        progressed = False
        for name in order:
            if buckets[name] and len(kept) < cap:
                kept.append(buckets[name].pop(0))
                progressed = True
        if not progressed:
            break
    return kept, len(entries)


def discover(
    root_url: str,
    user_agent: str,
    delay: float,
    max_pages_per_host: int,
    slug: str = "",
    fetcher: Fetcher | None = None,
    scope_terms: Iterable[str] = (),
) -> DiscoverResult:
    parts = urlsplit(root_url.strip())
    scheme, host = parts.scheme or "https", (parts.hostname or "").lower()
    domain = urls.registrable_domain(host)
    fetcher = fetcher or Fetcher(user_agent, delay)
    robots = Robots(fetcher)
    result = DiscoverResult(
        urls.canonicalize(root_url), host, domain, workspace.iso(workspace.utc_now())
    )
    hosts = [host] + [
        f"{sub}.{domain}" for sub in discover_rules.PROBE_SUBDOMAINS if f"{sub}.{domain}" != host
    ]
    per_host: dict[str, dict[str, dict[str, Any]]] = {}
    terms = set(scope_terms)

    def add(url: str, source: str) -> None:
        canonical = urls.canonicalize(url)
        h = (urlsplit(canonical).hostname or "").lower()
        if urls.registrable_domain(h) != domain:
            return
        if h not in per_host and len(per_host) >= MAX_HOSTS:
            return
        bucket = per_host.setdefault(h, {})
        if canonical in bucket:
            if source == "homepage":
                bucket[canonical]["nav"] = True
            return
        bucket[canonical] = {
            "url": url,
            "canonical_url": canonical,
            "host": h,
            "category": discover_rules.classify(canonical, domain, slug),
            "allowed": robots.allowed(canonical),
            "source": source,
            "nav": source == "homepage",
        }

    for i, h in enumerate(hosts):
        robots_resp = robots.load(scheme, h)
        if robots_resp.status == 0:
            result.probes.append(
                {"host": h, "live": False, "status": 0, "error": robots_resp.error}
            )
            if i == 0:
                result.errors.append(
                    {"url": robots_resp.url, "status": 0, "error": robots_resp.error}
                )
            continue
        home = f"{scheme}://{h}/"
        live = True
        if i > 0:  # probe
            if robots.allowed(home):
                head = fetcher.fetch(home, method="HEAD")
                if head.status == 405:
                    head = fetcher.fetch(home)
                live = 0 < head.status < 500 and head.status not in (404, 410)
                result.probes.append({"host": h, "live": live, "status": head.status})
            else:
                result.probes.append({"host": h, "live": True, "status": None,
                                      "note": "homepage disallowed by robots.txt"})  # fmt: skip
        if not live:
            continue
        add(home, "probe" if i else "homepage")
        for loc in _sitemap_locs(fetcher, robots, scheme, h, domain, result.errors):
            add(loc, "sitemap")
        if i == 0 and robots.allowed(home):
            resp = _follow(fetcher, robots, home, domain)
            if resp.ok:
                parser = _Links()
                parser.feed(resp.text())
                external: dict[str, dict[str, Any]] = {}
                for href in parser.hrefs:
                    absolute = urljoin(home, href)
                    if urlsplit(absolute).scheme not in ("http", "https"):
                        continue
                    target_host = (urlsplit(absolute).hostname or "").lower()
                    if urls.registrable_domain(target_host) == domain:
                        add(absolute, "homepage")
                    else:
                        canonical = urls.canonicalize(absolute)
                        external.setdefault(canonical, {
                            "url": absolute,
                            "canonical_url": canonical,
                            "category": discover_rules.classify(canonical, domain, slug),
                            "source": "homepage-link",
                            "fetched": False,
                        })  # fmt: skip
                result.external = list(external.values())
            elif resp.status:
                result.errors.append({"url": home, "status": resp.status, "error": resp.error})
        if i == 0:
            _probe_paths(fetcher, robots, scheme, h, domain, per_host.get(h, {}), add)

    for h in sorted(per_host):
        entries = list(per_host[h].values())
        kept, dropped = _cap_ranked(entries, max_pages_per_host, terms)
        result.truncated += dropped
        result.entries.extend(sorted(kept, key=lambda e: e["canonical_url"]))
    result.disallowed = sum(1 for e in result.entries if not e["allowed"])
    result.requests = len(fetcher.requests)
    return result


def write_cache(ws: Path, result: DiscoverResult) -> Path:
    directory = workspace.pf_dir(ws) / workspace.CACHE / "discover"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{result.host}.json"
    atomic_write_text(path, json.dumps(result.to_dict(), indent=2) + "\n")
    return path


def cache_paths(ws: Path) -> list[Path]:
    directory = workspace.pf_dir(ws) / workspace.CACHE / "discover"
    return sorted(directory.glob("*.json")) if directory.is_dir() else []


def load_cache(ws: Path) -> list[dict[str, Any]]:
    directory = workspace.pf_dir(ws) / workspace.CACHE / "discover"
    if not directory.is_dir():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("*.json"))]
