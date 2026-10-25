"""discover.py against a local multi-host server — no real network, no DNS."""

from __future__ import annotations

import gzip
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from conftest import FIXTURES

from pflib import discover, discover_rules

SITE = FIXTURES / "http" / "tasklet"
SERVED = ["tasklet.example", "docs.tasklet.example", "status.tasklet.example",
          "developers.tasklet.example", "api.tasklet.example"]  # fmt: skip


class Handler(BaseHTTPRequestHandler):
    log: list[tuple[str, str, str]] = []

    def log_message(self, *args: object) -> None:  # silence
        pass

    def _route(self) -> tuple[int, dict[str, str], bytes]:
        host = (self.headers.get("Host") or "").split(":")[0].lower()
        path = self.path.split("?", 1)[0]
        type(self).log.append((self.command, host, self.path))
        if host == "api.tasklet.example":
            return 500, {}, b"boom"
        if host == "developers.tasklet.example" and path == "/robots.txt":
            return 403, {}, b"forbidden"
        if host == "tasklet.example" and path == "/go/blog":
            return 302, {"Location": "/blog/post-01"}, b""
        if host == "tasklet.example" and path == "/go/out":
            return 302, {"Location": "https://evil.example/landing"}, b""
        if host == "tasklet.example" and path == "/sitemap-docs.xml.gz":
            raw = (SITE / host / "sitemap-docs.xml").read_bytes()
            return 200, {"Content-Type": "application/gzip"}, gzip.compress(raw)
        rel = "index.html" if path in ("", "/") else path.lstrip("/")
        file = SITE / host / rel
        if file.is_file():
            return 200, {"Content-Type": "text/html"}, file.read_bytes()
        return 404, {}, b"not found"

    def _send(self, with_body: bool) -> None:
        status, headers, body = self._route()
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if with_body:
            self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        self._send(True)

    def do_HEAD(self) -> None:  # noqa: N802
        self._send(False)


@pytest.fixture
def site() -> Iterator[dict[str, str]]:
    Handler.log = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    addr = f"127.0.0.1:{server.server_address[1]}"
    try:
        yield {host: addr for host in SERVED}
    finally:
        server.shutdown()


def run(
    site: dict[str, str], max_pages: int = 40
) -> tuple[discover.DiscoverResult, discover.Fetcher]:
    sleeps: list[float] = []
    fetcher = discover.Fetcher(
        "ProductForge-test/1.0", delay=0.5, host_map=site, sleep=sleeps.append
    )
    result = discover.discover("http://tasklet.example/", "ProductForge-test/1.0", 0.5, max_pages,
                               slug="tasklet", fetcher=fetcher)  # fmt: skip
    assert sleeps == [0.5] * (len(fetcher.requests) - 1)  # polite delay between every request
    return result, fetcher


def by_url(result: discover.DiscoverResult) -> dict[str, dict]:
    return {e["canonical_url"]: e for e in result.entries}


def test_never_requests_a_disallowed_url(site: dict[str, str]) -> None:
    result, fetcher = run(site)
    requested_paths = [path for _, _, path in Handler.log]
    assert not any(p.startswith(("/admin", "/private")) for p in requested_paths)
    entries = by_url(result)
    assert entries["http://tasklet.example/admin/secret"]["allowed"] is False
    assert entries["http://tasklet.example/private/roadmap"]["allowed"] is False
    assert result.disallowed >= 2
    # developers.* serves robots.txt with 403 → everything there is disallowed and untouched
    assert ("GET", "developers.tasklet.example", "/robots.txt") in Handler.log
    assert not [
        r for r in Handler.log if r[1] == "developers.tasklet.example" and r[2] != "/robots.txt"
    ]


def test_classification_sources_and_canonical_urls(site: dict[str, str]) -> None:
    result, _ = run(site)
    entries = by_url(result)
    expected = {
        "http://tasklet.example/": "homepage",
        "http://tasklet.example/pricing": "pricing",
        "http://tasklet.example/features/boards": "features",
        "http://tasklet.example/security": "security",
        "http://tasklet.example/changelog": "changelog",
        "http://tasklet.example/integrations/calendar": "integrations",  # utm stripped
        "http://tasklet.example/enterprise": "enterprise",
        "http://tasklet.example/docs/tasks": "docs",  # from the gzipped sitemap
        "http://tasklet.example/help/guests": "help-center",
        "http://tasklet.example/blog/post-01": "product-blog",
        "http://docs.tasklet.example/getting-started": "docs",
        "http://docs.tasklet.example/api/tasks": "api-docs",
        "http://status.tasklet.example/": "status",
    }
    for url, category in expected.items():
        assert entries[url]["category"] == category, url
    assert entries["http://tasklet.example/about"]["category"] == "company"
    assert entries["http://tasklet.example/pricing"]["source"] in ("sitemap", "homepage")
    assert entries["http://status.tasklet.example/"]["source"] == "probe"
    assert not any("elsewhere.example" in u for u in entries)  # off-site sitemap ignored


def test_external_links_are_recorded_not_fetched(site: dict[str, str]) -> None:
    result, fetcher = run(site)
    external = {e["canonical_url"]: e for e in result.external}
    assert external["https://github.com/tasklet"]["category"] == "official-repo"
    assert external["https://github.com/someone/tasklet-cli"]["category"] == "github"
    assert external["https://www.youtube.com/@tasklet"]["category"] == "youtube"
    assert external["https://x.com/tasklet"]["category"] == "social"
    assert all(e["fetched"] is False for e in result.external)
    assert not any(u.startswith(("mailto:", "javascript:")) for u in external)
    hosts_requested = {(u.split("/")[2]) for _, u in fetcher.requests}
    assert not hosts_requested & {"github.com", "www.youtube.com", "x.com", "evil.example"}


def test_redirects_followed_only_on_site(site: dict[str, str]) -> None:
    # /go/blog and /go/out are homepage links: discover records them but only follows redirects
    # for the URLs it fetches itself (homepage, sitemaps). Following off-site is never allowed.
    fetcher = discover.Fetcher("ua", 0, host_map=site)
    robots = discover.Robots(fetcher)
    ok = discover._follow(fetcher, robots, "http://tasklet.example/go/blog", "tasklet.example")
    assert ok.ok and ok.url == "http://tasklet.example/blog/post-01"
    out = discover._follow(fetcher, robots, "http://tasklet.example/go/out", "tasklet.example")
    assert out.status == 302 and "not followed" in (out.error or "")
    assert not any("evil.example" in u for _, u in fetcher.requests)


def test_well_known_paths_are_probed_only_when_missing(site: dict[str, str]) -> None:
    result, fetcher = run(site)
    entries = by_url(result)
    # /pricing is in the sitemap → "pricing" is covered, so neither /pricing nor /plans is probed
    assert ("HEAD", "http://tasklet.example/plans") not in fetcher.requests
    assert ("HEAD", "http://tasklet.example/pricing") not in fetcher.requests
    # /trust and /features are not covered by name but their categories are → not probed either
    assert ("HEAD", "http://tasklet.example/trust") not in fetcher.requests
    assert entries["http://tasklet.example/pricing"]["source"] in ("sitemap", "homepage")


def test_well_known_path_probe_finds_unlisted_pages(site: dict[str, str]) -> None:
    sitemap = SITE / "tasklet.example" / "sitemap-pages.xml"
    original = sitemap.read_text()
    try:
        sitemap.write_text(
            original.replace("<url><loc>http://tasklet.example/pricing</loc></url>", "")
        )
        index = SITE / "tasklet.example" / "index.html"
        html = index.read_text()
        index.write_text(html.replace('<a href="/pricing">Pricing</a>', ""))
        try:
            result, fetcher = run(site)
        finally:
            index.write_text(html)
    finally:
        sitemap.write_text(original)
    entries = by_url(result)
    assert ("HEAD", "http://tasklet.example/pricing") in fetcher.requests  # 404 here
    assert entries["http://tasklet.example/plans"]["source"] == "path-probe"
    assert entries["http://tasklet.example/plans"]["category"] == "pricing"


def test_probes_and_errors_never_raise(site: dict[str, str]) -> None:
    result, _ = run(site)
    probes = {p["host"]: p for p in result.probes}
    assert probes["docs.tasklet.example"]["live"] is True
    assert probes["status.tasklet.example"]["live"] is True
    assert probes["api.tasklet.example"]["live"] is False  # 500 on /
    assert (
        probes["help.tasklet.example"]["live"] is False
        and probes["help.tasklet.example"]["status"] == 0
    )


def test_cap_is_round_robin_across_categories(site: dict[str, str]) -> None:
    result, _ = run(site, max_pages=12)
    main = [e for e in result.entries if e["host"] == "tasklet.example"]
    assert len(main) == 12 and result.truncated > 0
    categories = {e["category"] for e in main}
    # 30 blog posts must not crowd out the rest
    assert {"pricing", "docs", "security", "changelog"} <= categories
    assert sum(1 for e in main if e["category"] == "product-blog") <= 2


def test_unreachable_root_reports_error(site: dict[str, str]) -> None:
    fetcher = discover.Fetcher("ua", 0, host_map={})
    result = discover.discover("http://nowhere.example/", "ua", 0, 40, fetcher=fetcher)
    assert result.entries == [] and result.errors and result.errors[0]["status"] == 0


def test_cache_round_trip(site: dict[str, str], tmp_path: Path) -> None:
    (tmp_path / ".productforge").mkdir()
    result, _ = run(site)
    path = discover.write_cache(tmp_path, result)
    assert path.name == "tasklet.example.json"
    (loaded,) = discover.load_cache(tmp_path)
    assert loaded["counts"] == result.counts() and loaded["host"] == "tasklet.example"


@pytest.mark.parametrize(
    "url, category",
    [
        ("https://docs.x.example/anything", "docs"),
        ("https://x.example/docs/a", "docs"),
        ("https://x.example/api/reference", "api-docs"),
        ("https://developers.x.example/", "api-docs"),
        ("https://x.example/blog/engineering/sync", "engineering-blog"),
        ("https://x.example/blog/launch", "product-blog"),
        ("https://x.example/webinars/intro", "official-demo"),
        ("https://x.example/trust", "security"),
        ("https://x.example/", "homepage"),
        ("https://x.example/careers", "company"),
        ("https://x.example/about", "company"),
        ("https://x.example/privacy", "company"),
        ("https://x.example/terms-of-service", "company"),
        ("https://x.example/legal/cookies", "company"),
        ("https://x.example/teams", None),
        ("https://x.example/solutions/litigation", "features"),
        ("https://x.example/solution/litigation", "features"),
        ("https://x.example/products/contracts", "features"),
        ("https://x.example/product/contracts", "features"),
        ("https://x.example/modules/billing", "features"),
        ("https://x.example/platform/overview", "features"),
        ("https://x.example/corporate/enterprise-contracts", "features"),
        ("https://x.example/enterprise-billing", "features"),
        ("https://x.example/enterprise", "enterprise"),
        ("https://x.example/trust", "security"),
        ("https://github.com/x/sdk", "official-repo"),
        ("https://www.g2.com/products/x", "review-sites"),
        ("https://unknown.example/a", None),
    ],
)
def test_rules(url: str, category: str | None) -> None:
    assert discover_rules.classify(url, "x.example", slug="x") == category


class FakeSite(discover.Fetcher):
    """Serves one host: a homepage linking one page, and a sitemap of 300 help articles."""

    def __init__(self) -> None:
        super().__init__("ua", 0)
        locs = [f"https://big.example/help/how-to-{i}" for i in range(300)]
        locs += [f"https://big.example/help/matter-intake-{i}" for i in range(10)]
        locs += [f"https://big.example/corporate/enterprise-module-{i}" for i in range(5)]
        self.sitemap = "".join(f"<url><loc>{u}</loc></url>" for u in locs)

    def fetch(self, url: str, method: str = "GET") -> discover.Response:
        path = url.split("big.example", 1)[-1]
        if not url.startswith("https://big.example/"):
            return discover.Response(url, 0, error="no host")
        if path == "/sitemap.xml":
            body = f"<urlset>{self.sitemap}</urlset>".encode()
        elif path == "/":
            body = b'<a href="/pricing">Pricing</a><a href="/help/how-to-7">x</a>'
        else:
            return discover.Response(url, 404)
        return discover.Response(url, 200, {}, body)


def ranked(terms: set[str], cap: int = 50) -> discover.DiscoverResult:
    return discover.discover("https://big.example/", "ua", 0, cap, fetcher=FakeSite(),
                             scope_terms=terms)  # fmt: skip


def test_ranked_cap_keeps_modules_navigation_and_scope_matches() -> None:
    result = ranked({"matter", "intake"})
    urls = {e["canonical_url"]: e for e in result.entries}
    assert len(urls) == 50 and result.truncated == 317 - 50  # 300+10+5 + home + pricing
    for i in range(5):  # every module page survives, though it is a minority
        assert f"https://big.example/corporate/enterprise-module-{i}" in urls
    for i in range(10):  # scope-matching articles
        assert f"https://big.example/help/matter-intake-{i}" in urls
    nav = urls["https://big.example/help/how-to-7"]
    assert nav["nav"] is True and nav["source"] == "sitemap"  # sitemap listed it first
    assert urls["https://big.example/pricing"]["nav"] is True
    unrelated = [u for u in urls if "how-to-" in u and not urls[u]["nav"]]
    assert len(unrelated) <= 50 - 15  # the long tail is what gets cut


def test_ranked_entries_carry_rank_scope_hits_and_nav() -> None:
    result = ranked({"matter", "intake"})
    ranks = sorted(e["rank"] for e in result.entries)
    assert ranks == list(range(1, 51))
    by = {e["canonical_url"]: e for e in result.entries}
    assert by["https://big.example/help/matter-intake-3"]["scope_hits"] == 2
    assert by["https://big.example/"]["nav"] is True
    best = min(result.entries, key=lambda e: e["rank"])
    assert best["nav"] is True  # navigation outranks scope hits


def test_without_terms_round_robin_fallback_is_unchanged() -> None:
    entries = [
        {"url": f"https://x.example/blog/p{i}", "canonical_url": f"https://x.example/blog/p{i}",
         "category": "product-blog"} for i in range(30)
    ] + [
        {"url": f"https://x.example/{p}", "canonical_url": f"https://x.example/{p}",
         "category": c} for p, c in [("docs/a", "docs"), ("pricing", "pricing"),
                                     ("security/x", "security")]
    ]  # fmt: skip
    kept, dropped = discover._cap_ranked(entries, 4)
    assert dropped == 29 and {e["category"] for e in kept} == {
        "docs",
        "pricing",
        "security",
        "product-blog",
    }
    assert [e["rank"] for e in kept] == [1, 2, 3, 4]
    assert all(e["scope_hits"] == 0 and e["nav"] is False for e in kept)


def test_old_cache_entries_without_new_fields_still_load(tmp_path: Path) -> None:
    from pflib import workspace

    d = workspace.pf_dir(tmp_path) / workspace.CACHE / "discover"
    d.mkdir(parents=True)
    (d / "old.example.json").write_text('{"host": "old.example", "entries": [{"url": "u"}]}')
    (cache,) = discover.load_cache(tmp_path)
    assert cache["entries"][0].get("rank", 0) == 0
