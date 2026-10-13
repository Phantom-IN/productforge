# ProductForge v1 — dogfood report

How v1 measured up against its success criteria (IDEA §51, IMPLEMENTATION_PLAN §1) on real use.
Only aggregate numbers and paraphrased observations are recorded here; the research workspaces
themselves are not committed.

## What was run

| Run | Product | Stages | Size |
|---|---|---|---|
| **Real product** | Plausible Analytics (public docs; chosen over Linear for its complete, robots-friendly documentation) — scope "web analytics dashboard" | DISCOVERY → PRODUCT_MODEL: research, features, workflows, domain model | 79 sources · 324 claims · 46 unknowns · 18 surfaces · 248 features in 9 domains · 18 workflows · 41 entities · 7 roles · 66 permission rules |
| **Small chain** | Tasklet (synthetic, `.example` domains) starting from the PRODUCT_MODEL fixture | integrations + inference → competitors (one real competitor, Todoist) → scope → architect → finalize → trace → complete | 8 integrations · 34 inferences · 31 score cards · 15 requirements · 15 ADRs · 11 invariants · 18 phases |

Every command ran in a headless `claude --plugin-dir .` session. The later stages ran on the small
workspace to keep token use proportionate; a full real-product run through `finalize` is the first
v1.1 item.

## Success criteria

| Criterion (IDEA §51) | Result | Evidence |
|---|---|---|
| Trustworthy source inventory | **Met** | 79 tiered sources, DISCOVERY gate 10/10; spot-check below: 9/10 claims accurate, 1 partial, 0 wrong |
| Coherent feature breakdown | **Met** | 9 domains, 248 features, every surface mapped (0 validator errors) |
| Major workflows | **Met** | 18 workflows covering all 9 domains; 121 observed and 148 implied-system steps |
| Domain model | **Met, with a v1.1 note** | 41 entities, tree rooted at the tenancy entity; some UI state was modelled as entities |
| Permission model | **Met** | 66 rules × 7 roles, no missing cell; 25 % `?` cells, each tied to an unknown |
| Integration inventory | **Partial** | 8 integrations on the small chain; not run on the real product (v1.1) |
| Architecture requirements | **Partial** | 34 inferences, 30 with target UNKNOWN, all measurable; not run on the real product (v1.1) |
| MVP recommendation | **Partial** | scored and decided by script; the user moved one feature, recorded as an override; small chain only |
| Parity matrix | **Partial** | generated from 31 score cards; small chain only |
| Independent architecture | **Partial** | 14 ADRs + 10 invariants, both stack preferences used, one decision changed and superseded; small chain only |
| Complete implementation plan | **Partial** | 21-section plan, golden rules = invariants; small chain only |
| Ordered executable phases | **Partial** | 18 phases, `lint-phases` 0 findings; small chain only |
| A fresh session starts with `execute phase 00` | **Met** | given only `STARTUP_PROMPT.md`, a new session read the files, summarised the project and waited for `execute phase NN` |
| Every phase traces to evidence | **Met** | `pf.py trace`: 15/15 requirements traced from a public source to a phase; gate 7/7 |
| `pf.py check` passes on the workspace | **Met** | 0 errors on every stage of both runs |

"Partial" means the capability works end to end and is gate-checked, but was exercised on the
synthetic small chain rather than on the real product.

## Claim spot-check (10 random CONFIRMED claims, real product)

Each claim was compared with the page it cites.

| Result | Count | Notes |
|---|---:|---|
| Accurate | 9 | attribution model, graph intervals, search-keyword source, page blocking limits, shared-link seats, data exports, property deletion, annotations, blog history |
| Partial | 1 | D-127: the channel list is right, but the page lists about 19 channels, not 18 |
| Inaccurate | 0 | |

## Traceability walk (`pf.py explain`, small chain)

| Requirement | Sources | Claims | Features / workflows | ADRs | Phases |
|---|---:|---:|---:|---|---|
| R-001 tenancy boundary | 3 | 5 | 5 | ADR-014 | 01, 03, 04, 07 … 17 |
| R-003 hosted sign-in | 2 | 3 | 4 | ADR-003 | 02, 06 |
| R-009 projects | 2 | 4 | 3 | ADR-013 | 00, 01, 05, 07 … 17 |
| R-011 board freshness | 8 | 10 | 9 | ADR-001, ADR-015 | 00, 05, 09, 13, 16, 17 |
| R-014 attachments | 2 | 2 | 1 | ADR-009, ADR-012 | 02, 06, 14, 15, 17 |

Every chain reaches a Tier 1–2 source upstream and at least one phase downstream.

## Defects found and fixed during the runs

- Agents spawned every domain pass at once and hit usage limits → run limits, `staging list/discard`, a "resume first" step.
- A near-duplicate warning kept firing after duplicates were superseded → inactive records skipped.
- 248 features against a soft cap of 120 → per-domain budgets in briefs.
- Wrapped workflow steps lost their citations → continuation lines joined.
- Research requests other than "browse" had no handler → a general research-request protocol.
- A corrected permission rule merged into the old one, dropping its cells → title dedupe + one rule per resource × action.
- A re-run could not add a competitor's offered features; one competitor showed every feature as "rare"; the source budget was exceeded → union field, rarity needs ≥ 2 competitors, `competitors.max_sources`.
- Proposals could not follow a superseded decision → amendable proposals + a stale-citation warning.
- Phase lint misread `IDEA §…` lists and stripped the dot from `.claude-plugin/` → document context by parenthesis depth, prefix-safe path handling; six of ProductForge's own task lines now name their files.
- Traceability chains walked structural links (task → workspace → everything) → provenance edges only.

## Calibration

| Knob | Before | After | Evidence |
|---|---|---|---|
| `research.min_sources_gate` | 15 | 15 | the real product reached 79; the synthetic fixture passes with 20 |
| `research.min_claims_gate` | 40 | 40 | 324 on the real product, 42 active on the fixture |
| `scope.build_threshold` / `scope.defer_threshold` | 18 / 8 (plan) | **6 / −4** | calibrated in Phase 13: 18/8 left 5 of 31 features in V1; the live scope run produced 12 build / 3 external / 10 defer / 6 drop |
| near-duplicate ratio | 0.92 | 0.92 | false positives came only from titles that differ by an ID; fixed in the titles, not the ratio |

## v1.1 follow-ups

See [`plans/v1.1/README.md`](../plans/v1.1/README.md).
