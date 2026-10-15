"""URL → source-category classification for discovery.

Ordered rules; the first match wins. Categories are names from ``taxonomy.CATEGORIES``.
Rules only *propose* a category: the research agent may pick a narrower true one (and may only
lower, never raise, the tier).
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from pflib import urls

# Subdomains of the target's registrable domain that discovery probes.
PROBE_SUBDOMAINS: tuple[str, ...] = (
    "docs", "help", "support", "developers", "developer", "api", "status", "changelog",
)  # fmt: skip

# Paths probed on the root host (HEAD, robots-checked) when sitemaps/homepage did not list them —
# key official pages are often missing from sitemaps or linked only via scripts.
WELL_KNOWN_PATHS: tuple[str, ...] = (
    "/pricing", "/plans", "/docs", "/changelog", "/security", "/trust", "/integrations",
    "/enterprise", "/features",
)  # fmt: skip

# (host pattern, path pattern, category) for URLs on the target's own site. ``None`` = any.
ON_SITE_RULES: tuple[tuple[str | None, str | None, str], ...] = (
    (r"^status\.", None, "status"),
    (r"^changelog\.", None, "changelog"),
    (r"^(developers?|api)\.", None, "api-docs"),
    (r"^(help|support)\.", None, "help-center"),
    (None, r"/(api|developers?|reference)(/|$)", "api-docs"),
    (r"^docs\.", None, "docs"),
    (None, r"/(docs|documentation|guides?|manual)(/|$)", "docs"),
    (None, r"/(help|support|faq|kb|knowledge-base)(/|$)", "help-center"),
    (None, r"/(changelog|releases?|release-notes|whats-new|updates)(/|$)", "changelog"),
    (None, r"/(security|trust|compliance|privacy|gdpr|soc-?2)(/|$)", "security"),
    (None, r"/(pricing|plans)(/|$)", "pricing"),
    (None, r"/(enterprise)(/|$)", "enterprise"),
    (None, r"/(integrations?|apps|marketplace|extensions)(/|$)", "integrations"),
    (None, r"/(blog/)?engineering(/|$)", "engineering-blog"),
    (None, r"/(blog|news|announcements)(/|$)", "product-blog"),
    (None, r"/(webinars?|demos?|videos?)(/|$)", "official-demo"),
    (None, r"/(tutorials?|academy|learn|courses?)(/|$)", "official-tutorial"),
    (None, r"/(features?|product|platform|solutions?|use-cases)(/|$)", "features"),
    (None, r"^/?$", "homepage"),
)

# (host pattern, category) for links that leave the target's site (recorded, never fetched).
OFF_SITE_RULES: tuple[tuple[str, str], ...] = (
    (r"(^|\.)github\.com$", "github"),
    (r"(^|\.)gitlab\.com$", "github"),
    (r"(^|\.)(youtube\.com|youtu\.be|vimeo\.com)$", "youtube"),
    (r"(^|\.)producthunt\.com$", "product-hunt"),
    (r"(^|\.)reddit\.com$", "reddit"),
    (r"(^|\.)(twitter\.com|x\.com|linkedin\.com|mastodon\.social|bsky\.app|threads\.net)$",
     "social"),
    (r"(^|\.)(g2\.com|capterra\.com|trustradius\.com|getapp\.com)$", "review-sites"),
    (r"(^|\.)(medium\.com|dev\.to|hashnode\.com|substack\.com)$", "technical-blogs"),
)  # fmt: skip


def classify(url: str, target_domain: str, slug: str = "") -> str | None:
    """Category for ``url``; ``None`` when nothing matches (the agent decides)."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    path = parts.path or "/"
    if urls.registrable_domain(host) == target_domain:
        for host_re, path_re, category in ON_SITE_RULES:
            if host_re and not re.search(host_re, host):
                continue
            if path_re and not re.search(path_re, path, re.I):
                continue
            return category
        return None
    for host_re, category in OFF_SITE_RULES:
        if re.search(host_re, host):
            if category == "github" and slug and _owner(path) == slug:
                return "official-repo"
            return category
    return None


def _owner(path: str) -> str:
    segment = path.strip("/").split("/", 1)[0]
    return re.sub(r"[^a-z0-9]+", "-", segment.lower()).strip("-")
