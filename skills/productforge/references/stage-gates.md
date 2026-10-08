# Stage gates

ProductForge's lifecycle is a state machine (IMPLEMENTATION_PLAN.md §7) enforced by
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
| `/productforge features` · `workflows` · `model` · `competitors` | PRODUCT_MODEL |
| `/productforge scope` | SCOPE_DEFINED |
| `/productforge architect` | ARCHITECTURE_LOCKED |
| `/productforge finalize` | PHASE_PLAN_READY |
| `/productforge status` · `reopen <STAGE> --reason "…"` | any |

`pf.py status` suggests the next command: keep working on the open stage until its gate passes,
then the primary command of the next stage (`research`, `features`, `scope`, `architect`,
`finalize`).

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

### PHASE_PLAN_READY

| Condition | Checks | Built in |
|---|---|---|
| `G-STATE-FILE-VALID` | state.json is present and valid | Phase 02 |
| `G-NO-UNMERGED-STAGING` | no staging run is waiting to be merged | Phase 02 |
| `G-VALIDATE-CLEAN` | pf.py validate reports no errors for this stage | Phase 03 |
| `G-PP-ROOT-DOCS` | root documents exist with required sections | Phase 15 |
| `G-PP-PHASE-LINT` | pf.py lint-phases is clean | Phase 15 |
| `G-PP-TRACE-CLEAN` | pf.py trace reports no errors | Phase 16 |
| `G-PP-TRACEABILITY-RENDERED` | TRACEABILITY.md matches a fresh render | Phase 16 |

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
