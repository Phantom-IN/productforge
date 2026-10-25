# Research playbook

How ProductForge researches a product during DISCOVERY. The goal of
this stage is a **trustworthy source ledger** that covers the product's official material and a
balanced sample of independent views — not a crawl.

## The loop

1. `pf.py discover <url>` — robots-aware reconnaissance: sitemaps, homepage links, subdomain probes.
   It reads no page content; it proposes candidate URLs with a category and `allowed` flag.
2. `pf.py research-plan` — coverage per category, candidates and source budget per partition, and
   whether a scope must be chosen first. The orchestrator follows these numbers; agents never
   invent budgets.
3. One research-agent run per partition (in parallel), each with its share of the budget.
4. Preflight, repair, merge, validate — then repeat `research` until coverage is good. Claims and
   unknowns are extracted in the evidence pass (Phase 07).

## Partitions

| Partition | Categories | How sources are found |
|---|---|---|
| `official-core` | homepage, features, pricing, enterprise, integrations, product-blog, official demos/talks/tutorials | discover cache |
| `official-docs` | docs, api-docs, help-center, changelog, security, status, engineering-blog, official-repo | discover cache (+ PDFs, repos) |
| `external` | tutorials, reviews, technical blogs, comparisons, videos, talks, GitHub, Product Hunt, Reddit, forums, social | web search (or the `research.deep` provider) |

## What each category is good for

| Category | Extract | Watch out for |
|---|---|---|
| docs, help-center | Objects, fields, states, limits, permissions, workflows | Old versions; pages marked legacy (lower the tier) |
| api-docs | Resource names, IDs, relationships, auth, pagination, webhooks | Beta endpoints |
| changelog | Recent capabilities, cadence, renamed features | Announcements of things not yet shipped |
| pricing, enterprise | Plan gating, seats, limits, SSO/SAML, audit features | Marketing names for the same feature |
| features, homepage | Positioning, major areas, target users | Superlatives — record the capability, not the claim |
| security, status | Compliance, encryption, regions, uptime history | Compliance claims ≠ architecture facts |
| engineering-blog, official talks | Observable behaviour (sync, offline, scale) | Never treat internals as *our* requirement without inference |
| reviews, community, social | What users rely on, complaints, missing features | Single anecdotes; competitor confusion |

## Query patterns (external partition)

- `"<product>" review` · `"<product>" vs` · `"<product>" alternatives`
- `"<product>" site:reddit.com` · `"<product>" site:news.ycombinator.com`
- `"<product>" tutorial` · `how to <core task> in <product>`
- `"<product>" github` · `"<product>" api example`
- Add the accepted scope's key noun: `"<product>" <scope noun> review`.

Prefer pages that are specific, dated and independent of each other (distinct sites matter for
PROBABLE claims). Skip SEO listicles that only repeat marketing copy.

## Budgets

`research.max_sources` (default 80) caps the ledger; `pf.py research-plan` splits what is left
across partitions (about 45% docs, 25% core, 30% external; official partitions never get more than
their candidates). Merge drops new, unreferenced sources over the cap and reports them.

## Claim granularity

A claim is **one observable behaviour a user could check** in the product.

| Too coarse | Right size | Too fine / not a claim |
|---|---|---|
| "Tasklet has great task management" | "A task has at most one assignee" | "The assign button is blue" |
| "Rich integrations" | "Due dates can be synced to an external calendar" | "Integrations are delightful" |
| "Enterprise-ready security" | "Data is encrypted at rest" | "They probably use AES on Postgres" (internals — never) |

Write one claim per behaviour, even when one page states many. Prefer the wording of the strongest
source, paraphrased. Engineering consequences ("needs a multi-entity search index") are separate
`INFERRED` claims `Derived from` the observation.

## Stale or contradictory material

- Prefer the newest official page; lower the tier of pages marked legacy/deprecated and say why.
- Do not resolve contradictions by picking a side silently — they become conflicting claims with an
  unknown or a written Resolution (`confidence-rules.md`).

## Claim context

Give every claim about a rule or behaviour a `Context`: the workflow, feature, screen or setting it
is about (use the workflow or screen name, not a vague word like "approvals"). A conflict exists only
between claims of the same context. Worked example, two true claims:

```markdown
### D-?1 — Clause-deviation approvals restart at Level 1
- Context: Clause-deviation approval workflow
### D-?2 — Contract-creation approvals resume at the rejecting level
- Context: Contract-creation approval workflow
```

They look contradictory but describe different workflows. Keep both, without `conflicting-with`; if
they were already marked, add `Resolution: different contexts — clause approvals vs creation
approvals`. Never merge them into one lifecycle rule downstream.

## JavaScript-only sites

If WebFetch returns an empty shell, the agent lists the URL as `browse <url>`; the orchestrator
delegates it to the `web.browse` provider when one is available. Otherwise use WebSearch snippets only
to decide *whether* a page matters, never as its content, and record the gap as an unknown.

## Scope recommendation

Recommend a scope (2–4 options in `product-overview.md` → `## Recommended scope`) when no scope was
accepted and either the product has more than 8 major areas or discovery found more candidate pages
than `research.max_sources`. `pf.py research-plan` reports `recommend_scope` and the reasons; the
orchestrator asks the user and records the choice with `pf.py set-scope "<text>" --accepted
--source recommended`. Every later agent filters its work through the accepted scope.
