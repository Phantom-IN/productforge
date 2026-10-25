# Stage gates

ProductForge's lifecycle is a state machine enforced by
`scripts/pflib/state.py`, `gates.py` and `commands.py`. Read this before running any
`/productforge` command that changes stage.

```text
UNINITIALIZED → DISCOVERY → PRODUCT_MODEL → SCOPE_DEFINED → ARCHITECTURE_LOCKED → PHASE_PLAN_READY → IMPLEMENTATION
```

## Semantics

- The state names the **open stage**: the only stage whose artifacts may be created or changed.
- A command for the **next** stage needs a transition: `pf.py check-command <cmd>` returns
  `needs_transition` with the open stage's gate report. Show the report to the user, ask them to
  confirm, then run `pf.py advance --to <NEXT> --confirmed`. **One transition per command; never two.**
  The user confirms per transition, or once for the whole run through a recorded autonomy grant
  (`pf.py autonomy grant`); with an active grant `advance --to <NEXT> --auto` replaces the
  confirmation, the gate still must pass, and the move is logged `auto-advance`.
- `advance` without `--confirmed` only prints the report and never changes `state.json`.
  A failing gate exits 1 and never transitions.
- A command two or more stages ahead is **refused**, naming the stages that must be finished first.
- A command for a closed earlier stage is **refused** with the `reopen` hint.
- `status` and `reopen` are always allowed.
- `IMPLEMENTATION` is never entered by `advance`; it is reported once generated phases are being
  executed (Phase 15/16).

## Command → stage

| Command | Stage |
|---|---|
| `/productforge <url> [--scope "…"] [--out dir] [--name NAME]` | creates the workspace, opens DISCOVERY |
| `/productforge research` | DISCOVERY |
| `/productforge features` · `workflows` · `model` · `competitors` | PRODUCT_MODEL (`competitors` is also allowed while SCOPE_DEFINED is open) |
| `/productforge scope` | SCOPE_DEFINED |
| `/productforge architect` | ARCHITECTURE_LOCKED |
| `/productforge finalize` | PHASE_PLAN_READY |
| `/productforge status` · `reopen <STAGE> --reason "…"` | any |

`competitors` is an evidence-adding command, like `research` requests after DISCOVERY closes: while
SCOPE_DEFINED is open it is allowed, because new `C`, `FS` and `S` records are appends to a closed
stage (lock rules cover only existing records). From ARCHITECTURE_LOCKED on it is refused with the
`reopen PRODUCT_MODEL` hint.

`pf.py status` suggests the next command: keep working on the open stage until its gate passes,
then the primary command of the next stage (`research`, `features`, `scope`, `architect`,
`finalize`). Before `scope` it suggests `competitors` while fewer than `competitors.min_researched`
active `C` records exist and no competitors waiver is recorded; in SCOPE_DEFINED it suggests
`competitors` while `G-SC-COMPETITOR-SIGNAL` fails and there is no waiver.

## Gates

Every stage's gate lists **all** of its conditions up front, including ones whose checks are
built by later phases. An unbuilt condition reports `not_built` and fails, so a stage can never be
advanced on checks that do not exist yet. Condition statuses: `pass`, `fail`, `not_built`, `error`
(the check itself raised — e.g. a file failed to parse).

### DISCOVERY

| Condition | Checks | Built in |
|---|---|---|
| `G-STATE-FILE-VALID` | state.json is present and valid | Phase 02 |
| `G-NO-UNMERGED-STAGING` | no staging run is waiting to be merged | Phase 02 |
| `G-VALIDATE-CLEAN` | pf.py validate reports no errors for this stage | Phase 03 |
| `G-SCOPE-SET` | a scope is set and accepted | Phase 02 |
| `G-DISC-MIN-SOURCES` | at least research.min_sources_gate sources | Phase 07 |
| `G-DISC-TIER1` | at least one Tier 1 source | Phase 07 |
| `G-DISC-COVERAGE` | every official source category has a source or an unknown | Phase 07 |
| `G-DISC-OVERVIEW` | product-overview.md sections are filled | Phase 07 |
| `G-DISC-SURFACES` | at least one product surface | Phase 07 |
| `G-DISC-MIN-CLAIMS` | at least research.min_claims_gate active claims | Phase 07 |
| `G-DISC-SCOPE-DEPTH` | in-scope official pages are read or excluded (min_scope_depth) | Phase v3-01 |
| `G-DISC-NAV-PAGES` | every in-scope homepage-navigation page is read or excluded | Phase v3-01 |
| `G-DISC-UNKNOWNS-AUDITED` | no unknown has an unread page that probably answers it | Phase v3-01 |

### PRODUCT_MODEL

| Condition | Checks | Built in |
|---|---|---|
| `G-STATE-FILE-VALID` | state.json is present and valid | Phase 02 |
| `G-NO-UNMERGED-STAGING` | no staging run is waiting to be merged | Phase 02 |
| `G-VALIDATE-CLEAN` | pf.py validate reports no errors for this stage | Phase 03 |
| `G-PM-SURFACE-FEATURES` | every product surface maps to a feature | Phase 11 |
| `G-PM-FEATURE-EVIDENCE` | every feature cites evidence or is derived | Phase 11 |
| `G-PM-WORKFLOW-PER-DOMAIN` | every core domain has a workflow | Phase 11 |
| `G-PM-ENTITY-COMPLETE` | entities have identity, lifecycle, deletion semantics | Phase 11 |
| `G-PM-PERMISSIONS-COVERAGE` | mutable entities have permission rules | Phase 11 |
| `G-PM-INTEGRATIONS-COMPLETE` | integrations have direction and authentication | Phase 11 |
| `G-PM-INFERENCE-COMPLETE` | architecture inferences are complete | Phase 11 |

### SCOPE_DEFINED

| Condition | Checks | Built in |
|---|---|---|
| `G-STATE-FILE-VALID` | state.json is present and valid | Phase 02 |
| `G-NO-UNMERGED-STAGING` | no staging run is waiting to be merged | Phase 02 |
| `G-VALIDATE-CLEAN` | pf.py validate reports no errors for this stage | Phase 03 |
| `G-SC-ALL-SCORED` | every feature has a score card | Phase 13 |
| `G-SC-DECISIONS-COMPUTED` | decisions match a fresh pf.py score run | Phase 13 |
| `G-SC-OVERRIDES-REASONED` | every override has a reason | Phase 13 |
| `G-SC-PARITY-COMPLETE` | parity matrix has a row per feature | Phase 13 |
| `G-SC-REQUIREMENTS-COVER-BUILD` | every built feature maps to a requirement | Phase 13 |
| `G-SC-UNKNOWNS-DEFAULTED` | every unknown has a V1 default | Phase 13 |
| `G-SC-CONFLICTS-RESOLVED` | conflicting claims are resolved or explained | Phase 13 |
| `G-SC-COMPETITOR-SIGNAL` | enough competitors researched, or a recorded waiver | Phase v3-03 |
| `G-SC-HEADLINE-REVIEWED` | no headline feature is cut without an override | Phase v3-03 |

### ARCHITECTURE_LOCKED

| Condition | Checks | Built in |
|---|---|---|
| `G-STATE-FILE-VALID` | state.json is present and valid | Phase 02 |
| `G-NO-UNMERGED-STAGING` | no staging run is waiting to be merged | Phase 02 |
| `G-VALIDATE-CLEAN` | pf.py validate reports no errors for this stage | Phase 03 |
| `G-AR-REQUIREMENTS-ADDRESSED` | every requirement is addressed by an ADR | Phase 14 |
| `G-AR-INFERENCES-PROPOSED` | every inference has a proposed implementation | Phase 14 |
| `G-AR-INVARIANTS` | invariants exist and are enforced | Phase 14 |
| `G-AR-REPO-STRUCTURE` | repository structure is declared | Phase 14 |
| `G-AR-STACK-COMPLETE` | stack fully named | Phase 14 |
| `G-AR-MANDATORY-TOPICS` | mandatory ADR topics covered | Phase 14 |
| `G-AR-EXTERNAL-SERVICES` | every external service names a vendor and a vendor ADR | Phase v3-04 |
| `G-AR-TOOLCHAIN` | the toolchain is pinned and verified | Phase v3-04 |
| `G-AR-ENV-CONTRACT` | environment variables and local services are declared | Phase v3-04 |

### PHASE_PLAN_READY

| Condition | Checks | Built in |
|---|---|---|
| `G-STATE-FILE-VALID` | state.json is present and valid | Phase 02 |
| `G-NO-UNMERGED-STAGING` | no staging run is waiting to be merged | Phase 02 |
| `G-VALIDATE-CLEAN` | pf.py validate reports no errors for this stage | Phase 03 |
| `G-PP-ROOT-DOCS` | root documents exist with required sections | Phase 15 |
| `G-PP-PHASE-LINT` | pf.py lint-phases reports no error | Phase 15 |
| `G-PP-TRACE-CLEAN` | pf.py trace reports no errors | Phase 16 |
| `G-PP-TRACEABILITY-RENDERED` | TRACEABILITY.md matches a fresh render | Phase 16 |

## How the DISCOVERY conditions are measured

| Condition | Passes when |
|---|---|
| `G-DISC-MIN-SOURCES` | `research/sources.md` holds ≥ `research.min_sources_gate` (15) sources |
| `G-DISC-TIER1` | at least one source has `Tier: 1` |
| `G-DISC-COVERAGE` | every official category (`taxonomy.OFFICIAL`) has a source with that `Category`, or its line in `product-overview.md` `## Coverage` cites an existing `U-` record |
| `G-DISC-OVERVIEW` | `Product`, `One-line description`, `Target users`, `Category`, `Pricing model` and `Major areas` are non-empty and not the template placeholder |
| `G-DISC-SURFACES` | at least one `PS-` record |
| `G-DISC-MIN-CLAIMS` | ≥ `research.min_claims_gate` (40) *active* claims (not superseded or rejected) |
| `G-DISC-SCOPE-DEPTH` | of the in-scope candidates in the discovery caches (allowed, official category, `scope_hits >= 1` or homepage navigation), the share that is a source (same canonical URL) or listed in `.productforge/exclusions.json` is ≥ `research.min_scope_depth` (0.6); passes when the index has no in-scope candidate |
| `G-DISC-NAV-PAGES` | every in-scope homepage-navigation candidate on the target's own host is a source or excluded |
| `G-DISC-UNKNOWNS-AUDITED` | `research.unknown_audit` is empty: no active `U` has an unread, unexcluded candidate whose slug shares ≥ 2 stemmed tokens with its `Question` (also warned as `UNKNOWN_UNREAD_CANDIDATES`) |

Both thresholds are config knobs (`.productforge/config.json`), e.g. lower `research.min_claims_gate`
for a deliberately tiny product — the gate report always shows the numbers.

## How the PRODUCT_MODEL conditions are measured

| Condition | Passes when |
|---|---|
| `G-PM-SURFACE-FEATURES` | every active `PS` is cited by an active feature's `Surface` |
| `G-PM-FEATURE-EVIDENCE` | every active `F` has `Evidence` or `Derived from` |
| `G-PM-WORKFLOW-PER-DOMAIN` | every domain with ≥ 3 active features has a workflow citing one of them |
| `G-PM-ENTITY-COMPLETE` | ≥ 1 entity, and no entity has a missing/empty field, bad relationship or deletion kind |
| `G-PM-PERMISSIONS-COVERAGE` | ≥ 1 role and rule, and no missing cell, unexplained `?`/`Limited`, bad grant, duplicate rule or mutable entity without a rule |
| `G-PM-INTEGRATIONS-COMPLETE` | ≥ 1 integration, each with a valid `Direction` and an `Authentication` |
| `G-PM-INFERENCE-COMPLETE` | ≥ 1 inference, each with Observation, Confidence, Engineering implication and Our requirement; every workflow with `[implied-system]` steps is cited by an `A` record's `Derived from` |

`/productforge model` reports this gate but never advances; `/productforge scope` asks before
closing PRODUCT_MODEL.

## How the SCOPE_DEFINED conditions are measured

| Condition | Passes when |
|---|---|
| `G-SC-ALL-SCORED` | every active feature has exactly one active `SC` score card |
| `G-SC-DECISIONS-COMPUTED` | no score card has malformed scores, and `FEATURE_MATRIX.md`, `PARITY_MATRIX.md` and `PRODUCT_SPEC.md` equal a fresh render from `pf.py score` |
| `G-SC-OVERRIDES-REASONED` | every `Override decision` has an `Override reason` |
| `G-SC-PARITY-COMPLETE` | the generated parity matrix has a row for every active feature |
| `G-SC-REQUIREMENTS-COVER-BUILD` | every BUILD NOW / BUILD SIMPLIFIED / USE EXTERNAL SERVICE feature is in some active `R`'s `Features` |
| `G-SC-UNKNOWNS-DEFAULTED` | every active `U` has a `UD` (or a non-empty `V1 default`) |
| `G-SC-CONFLICTS-RESOLVED` | no `CONFLICT_UNRESOLVED` — the PRODUCT_MODEL-era warning blocks here |
| `G-SC-COMPETITOR-SIGNAL` | at least `competitors.min_researched` (2) active `C` records, or a waiver recorded with `pf.py waive competitors --reason "…" --confirmed` (detail: `waived: <reason>`); a waiver can be set only while DISCOVERY, PRODUCT_MODEL or SCOPE_DEFINED is open |
| `G-SC-HEADLINE-REVIEWED` | no `HEADLINE_FEATURE_CUT`: every headline feature (its `Evidence` or `Surface` cites a target source in a `scope.headline_categories` category) that computes DEFER or DROP has an `Override decision` (any decision, with its reason) |

`/productforge scope` reports this gate but never advances; `/productforge architect` asks before
closing SCOPE_DEFINED.

## How the ARCHITECTURE_LOCKED conditions are measured

| Condition | Passes when |
|---|---|
| `G-AR-REQUIREMENTS-ADDRESSED` | every active `R` is in an active ADR's `Satisfies` or under `## Convention-covered requirements` |
| `G-AR-INFERENCES-PROPOSED` | every active `A` has exactly one active `AP` |
| `G-AR-INVARIANTS` | ≥ 1 invariant, each `Enforced by` a test, middleware, db-constraint, lint or review |
| `G-AR-REPO-STRUCTURE` | `## Repository structure` holds a fenced tree that parses to ≥ 2 paths |
| `G-AR-STACK-COMPLETE` | `## Stack` has a table with every choice named (no TBD, `?`, unknown) |
| `G-AR-MANDATORY-TOPICS` | each mandatory topic has an ADR with that `Topic` or a line under `## Not applicable topics` |
| `G-AR-EXTERNAL-SERVICES` | `## External services` has a table where each row (`Capability`, `Vendor`, `ADR`, `Test stand-in`) names a vendor that is not TBD and cites active ADRs with `Topic: vendor`; a capability listed under `## Not applicable topics` is exempt; a product with none has one row `none` |
| `G-AR-TOOLCHAIN` | `## Toolchain` has a row for every concern in `architecture.toolchain_concerns`, each with a pinned `Version` (not TBD, `latest` or `*`) and `Verified` as `YYYY-MM-DD <registry or URL>` (the date is only checked for form: agents verify on the day with WebFetch, `pf.py` stays offline) |
| `G-AR-ENV-CONTRACT` | `## Environments` has ≥ 1 row with no empty or TBD cell, and `### Local services` lists ≥ 1 `- <service>: <image:tag>, <port>` |

`UNDECIDED_CHOICE` repeats the "nothing open" rule on every build document: it matches
`quality.undecided_phrases` (whole phrases, case-insensitive, HTML comments ignored) from
ARCHITECTURE_LOCKED on, so a plan cannot ship "the library choice is open".

`/productforge architect` reports this gate but never advances; `/productforge finalize` asks
before closing ARCHITECTURE_LOCKED.

## How the PHASE_PLAN_READY conditions are measured

| Condition | Passes when |
|---|---|
| `G-PP-ROOT-DOCS` | the five root documents exist with their required sections; CLAUDE.md has one golden rule per invariant |
| `G-PP-PHASE-LINT` | ≥ 1 phase file and `pf.py lint-phases` reports no error-level finding; the heuristic cross-phase warnings (`PHASE_USES_NON_DEP`, `PHASE_PATH_CREATOR_NOT_DEP`) are listed in the detail for the consistency review |
| `G-PP-TRACE-CLEAN` | `pf.py trace` reports no error (every V1 requirement planned, every ADR and invariant used, no scope leak) |
| `G-PP-TRACEABILITY-RENDERED` | `spec/TRACEABILITY.md` equals a fresh `pf.py trace --write` |

PHASE_PLAN_READY is the last stage: `pf.py complete --confirmed` records its completion once the
gate passes. `status` reports IMPLEMENTATION when a phase in `plans/README.md` has left `Not started`.

## Scope

DISCOVERY cannot close without an accepted scope (`G-SCOPE-SET`). `/productforge <url> --scope "…"`
sets and accepts it; otherwise the research agent recommends scopes and the user picks one, recorded
with `pf.py set-scope "<text>" --accepted --source recommended`. Scope can only change while
DISCOVERY is open.

## Locks and reopen (feedback loop)

- When a stage closes, `advance` snapshots every record it owns into `state.json` `locks`: per
  record, a hash of all fields except the reference-list ("union") fields, plus the set of union
  references.
- Closed-stage records are **append-only**: new records may still be merged (e.g. extra claims from
  a research request), and merge may **add** references to union fields (more `Evidence`). Any other
  change, or a removed reference, is a lock violation (`pf.py validate`, Phase 03).
- `pf.py reopen <STAGE> --reason "…"` re-opens an earlier stage: its locks and those of every later
  stage are dropped, and every later stage that had already been worked on becomes **stale**. Moving
  forward again re-passes each gate in order; entering a stale stage clears its stale flag.
- Every `init`, `advance`, `reopen`, `set-scope` and `merge` is logged to
  `.productforge/history.log` (JSONL).
