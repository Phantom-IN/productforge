"""Source categories and their default tiers (IMPLEMENTATION_PLAN.md §10.2–§10.3, IDEA §36).

A source's tier starts at its category default and may be **lowered** (worse, higher number)
by the agent with a reason in ``Notes`` — never raised. Human-readable version:
``references/source-tiers.md`` (a test keeps the two in sync).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    name: str
    tier: int
    official: bool
    description: str


CATEGORIES: tuple[Category, ...] = (
    # ---- official (the target company's own properties) ----
    Category("docs", 1, True, "Official product documentation"),
    Category("api-docs", 1, True, "Official API / developer documentation"),
    Category("help-center", 1, True, "Official help center / support articles"),
    Category("changelog", 1, True, "Official changelog / release notes"),
    Category("security", 1, True, "Official security, trust and compliance documentation"),
    Category("official-repo", 1, True, "Public repositories owned by the target organisation"),
    Category("homepage", 2, True, "Marketing homepage"),
    Category("features", 2, True, "Official feature / product pages"),
    Category("pricing", 2, True, "Official pricing and plan pages"),
    Category("enterprise", 2, True, "Official enterprise pages"),
    Category("integrations", 2, True, "Official integrations directory / marketplace listings"),
    Category("status", 2, True, "Official status page"),
    Category("engineering-blog", 2, True, "Official engineering blog"),
    Category("product-blog", 2, True, "Official product blog / announcements"),
    Category("official-demo", 2, True, "Official demo videos and webinars"),
    Category("official-talk", 2, True, "Talks and podcasts given by the target's staff"),
    Category("official-tutorial", 2, True, "Official tutorials and guides outside the docs"),
    # ---- external ----
    Category("tutorials", 3, False, "Reliable third-party tutorials"),
    Category("review-sites", 3, False, "Product review platforms"),
    Category("technical-blogs", 3, False, "Third-party technical blog posts"),
    Category("comparison-articles", 3, False, "Third-party comparison articles"),
    Category("youtube", 3, False, "Third-party videos"),
    Category("talks-podcasts", 3, False, "Third-party talks, interviews and podcasts"),
    Category("github", 3, False, "Third-party repositories, issues and discussions"),
    Category("product-hunt", 4, False, "Product Hunt pages and comments"),
    Category("reddit", 4, False, "Reddit threads"),
    Category("forums", 4, False, "Community forums"),
    Category("social", 4, False, "Social media posts"),
    Category("unverified", 5, False, "Unverified claims"),
    Category("provider-report", 5, False, "A delegated skill's report (cite its sources instead)"),
)

BY_NAME: dict[str, Category] = {c.name: c for c in CATEGORIES}
OFFICIAL: tuple[str, ...] = tuple(c.name for c in CATEGORIES if c.official)
TIERS = (1, 2, 3, 4, 5)
AUTHORITIES = ("High", "Medium", "Low")


def default_tier(category: str) -> int | None:
    found = BY_NAME.get(category)
    return found.tier if found else None
