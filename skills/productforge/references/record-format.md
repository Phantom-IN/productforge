# Record format

How every ProductForge artifact stores its records (IMPLEMENTATION_PLAN.md §6). The parser is
`scripts/pflib/records.py`; artifact paths and per-prefix schemas live in `scripts/pflib/catalog.py`.

## Grammar

A **record** is a level-3 heading `### <ID> — <title>` (em dash, single spaces), followed
immediately by a bullet list of `- Key: value` fields. A value continues on following lines indented
by exactly two spaces. The record ends at the first line that is neither a field nor a continuation
(normally a blank line).

```markdown
### D-041 — Issues may optionally belong to projects
- Claim: Issues may optionally belong to projects.
- Evidence: S-004, S-017
- Confidence: CONFIRMED
- Product impact: Project membership cannot be mandatory.
- Engineering impact: issues.project_id must be nullable.
- Status: active

### D-052 — Global search appears to span issues and projects
- Claim: Global search appears to span issues and projects.
- Evidence: S-021
- Confidence: PROBABLE
- Product impact: Users expect one search box for all object types.
- Engineering impact: The search abstraction must support multiple entity types;
  a dedicated search engine is not implied.
- Status: active
```

Rules:
- Any `###` heading starting with an ID-like token (`X-1`, `AB-?2`) is parsed as a record and must
  be well formed; other headings are prose. Headings inside fenced code blocks are ignored.
- Field keys are fixed per schema (see `catalog.py`); a key appears at most once per record.
- An empty value is written `- Key:` (no trailing space).
- Canonical form round-trips byte-for-byte; do not add trailing spaces or other indents.
- Matrices are GFM tables, by convention under a `## Matrix` heading. Where an artifact has both,
  **records are canonical**; tables in `<!-- pf:generated -->` regions are rendered from them.
- Reference fields hold comma-separated IDs; extra words around IDs are allowed
  (`E-003 (1:N, required)`), and only IDs with a known prefix count as references.

## ID prefixes

| Prefix | Object | Width | Artifact |
|---|---|---|---|
| `S` | Source | 3 | `research/sources.md` |
| `D` | Discovery claim | 3 | `research/DISCOVERY_LEDGER.md` |
| `U` | Unknown | 3 | `research/UNKNOWNS.md` |
| `UD` | Unknown's V1 default | 3 | `research/UNKNOWNS.md` `## V1 defaults` |
| `PS` | Product surface | 2 | `research/product-surfaces.md` |
| `F` | Feature | 3 | `research/FEATURE_MATRIX.md` |
| `W` | Workflow | 3 | `research/workflows/W-NNN-<slug>.md` (one per file) |
| `E` | Domain entity | 2 | `spec/DOMAIN_MODEL.md` |
| `RL` | Role | 2 | `spec/PERMISSIONS_MATRIX.md` `## Roles` |
| `PR` | Permission rule | 3 | `spec/PERMISSIONS_MATRIX.md` `## Rules` |
| `I` | Integration | 2 | `spec/INTEGRATIONS.md` |
| `A` | Architecture inference | 3 | `research/architecture-inference.md` |
| `AP` | Architecture proposal | 3 | `research/architecture-inference.md` `## Proposals` |
| `C` | Competitor | 2 | `research/COMPETITORS.md` |
| `FS` | Competitor feature signal | 3 | `research/COMPETITORS.md` `## Feature signals` |
| `SC` | Feature score card | 3 | `spec/PARITY_MATRIX.md` `## Scores` |
| `R` | Our requirement | 3 | `spec/PRODUCT_SPEC.md` `## Requirements` |
| `INV` | Invariant | 2 | `spec/ARCHITECTURE.md` `## Invariants` |
| `ADR` | Architecture decision | 3 | `spec/decisions/ADR-NNN-<slug>.md` (one per file) |

Width is the minimum zero padding; numbers past it simply grow (`E-100`).

## Identity rules

- IDs are allocated only by `pf.py` (`merge` or `next-id`), never typed by hand into canonical files.
- IDs are **never reused or renumbered**. Allocation continues from the highest number ever seen —
  in canonical files *or* in `.productforge/ids.json` (the high-water marks).
- Records are never deleted. A replaced record gets `Status: superseded-by <ID>`.

## Status values

`active` · `superseded-by <ID>` · `conflicting-with <ID>[, <ID>]` · `rejected` (with a `Reason:` field).

## Staging and provisional IDs

Agents never edit `research/` or `spec/`. They write into the staging folder of their run
(`pf.py staging new --role <role>` prints it), mirroring the workspace layout:

```text
.productforge/staging/<run-id>/research/sources.md
.productforge/staging/<run-id>/research/DISCOVERY_LEDGER.md
.productforge/staging/<run-id>/research/workflows/create-task.md   # any name; merge renames
.productforge/staging/<run-id>/raw/...                               # delegated output, never merged
```

- New records use **provisional IDs** `<PREFIX>-?<n>` (`S-?1`, `D-?7`), unique per prefix within a
  run. They may reference each other and existing final IDs.
- A staged record must not use a final ID. To add evidence to an existing record, stage a record
  with the same dedupe key (e.g. the same normalised claim); merge unions its reference lists into the
  existing record.
- `pf.py merge <run-id>` dedupes (per-schema key: canonical URL for sources, normalised claim for
  claims, `(Domain, Feature)` for features, …), allocates final IDs, rewrites every provisional
  reference, writes canonical files, archives the run to `staging/_merged/`, and logs to
  `.productforge/history.log`. It is all-or-nothing: on any error nothing is written.
- On a dedupe hit only **reference-list fields** are merged (union, existing text kept). Differing
  values in other fields keep the canonical value and are listed as `conflicts` in the merge report.
- Prose outside records in staged record files is ignored (counted as `ignored_prose_lines`).
  Document artifacts (e.g. `product-overview.md`) merge section by section: a staged `##` section
  replaces the canonical section with the same heading or is appended.

## Merge and CLI error codes

Returned by `pf.py` commands (exit 1 or 2, JSON `{"error": CODE, ...}`); nothing is written.

| Code | Meaning |
|---|---|
| `PARSE_ERROR` | A file being merged or read strictly has a malformed record (line number in the message) |
| `DUPLICATE_ID` | The same provisional ID is defined twice in one staging run, or a record ID twice in a file |
| `DANGLING_PROVISIONAL` | A provisional reference has no staged definition (merge aborted, nothing written) |
| `UNKNOWN_PREFIX` | An ID uses a prefix not in the table above |
| `STAGED_FINAL_ID` | A staged record uses a final ID instead of a provisional one |
| `WRONG_ARTIFACT` | A staged record's prefix does not belong in the file it was staged in |
| `UNKNOWN_ARTIFACT` | A staged file does not map to any catalog artifact |
| `BAD_RECORD_FILE` | A staged workflow/ADR file does not hold exactly one record |
| `MERGE_LOCKED` | Another merge holds `.productforge/merge.lock` |
| `ALREADY_MERGED` | The run was merged before |
| `NO_SUCH_RUN` / `BAD_RUN_ID` / `BAD_ROLE` | Invalid staging run or role name |
| `NO_WORKSPACE` | No `.productforge/` found at or above the working directory |
| `AMEND_TARGET_MISSING` / `AMEND_LOCKED` / `AMEND_FIELD_NOT_ALLOWED` / `AMEND_NO_REASON` | An amendment was refused (see Amendments) |
| `REVISE_TARGET_MISSING` / `REVISE_LOCKED` / `REVISE_NO_REASON` / `BAD_REVISION` | A record-file revision was refused (see Revisions) |

## Amendments

The only way to change an existing record. A staged block

```markdown
### AMEND D-218
- Status: superseded-by D-049
- Why: Same fact as D-049.
```

sets `Status`, `Reason` and/or `Resolution` (nothing else) on a record of the **open** stage; `Why`
is required and is written to `history.log`, not to the record. Merge refuses amendments, writing
nothing, with `AMEND_TARGET_MISSING`, `AMEND_LOCKED` (closed stage — `pf.py reopen`),
`AMEND_FIELD_NOT_ALLOWED` or `AMEND_NO_REASON`. Provisional IDs in values are rewritten.

## Revisions (record files)

A record file's **body** (a workflow's `## Steps`, an ADR's notes) changes with a staged file that
starts with `### REVISE <ID>` and a `- Why:` line, followed by the `##` sections to replace; other
sections and the header record stay as they are (header fields change through unions and
amendments). Open stage only; logged as a `revise` event. Refusals write nothing:
`REVISE_TARGET_MISSING`, `REVISE_LOCKED` (closed stage — `pf.py reopen`), `REVISE_NO_REASON`,
`BAD_REVISION` (not a record file, or no `##` section). A `### REVISE` heading in a records artifact
(`DISCOVERY_LEDGER.md`, `FEATURE_INVENTORY.md`, …) is refused with `BAD_REVISION` too: records
there change by stage-and-supersede — the corrected record with a provisional ID plus
`### AMEND <old ID>` / `- Status: superseded-by <provisional ID>` / `- Why: …`.

```markdown
### REVISE W-003
- Why: the new help page (D-?1) shows the invite needs an admin first.

## Steps

1. [observed] Admin opens Members and invites by email — D-?1
```

## Generated regions

Tables and trees that are views over records live between `<!-- pf:generated:start <name> -->` and
`<!-- pf:generated:end -->`. `pf.py render` (and every merge) rebuilds them; never edit inside the
markers (`GENERATED_REGION_EDITED`). Prose sections without records in a records file (e.g.
`## Domains` in `FEATURE_MATRIX.md`) are merged section by section like documents.

## Domain and permission fields

Entities (`E`), roles (`RL`) and permission rules (`PR`) use small grammars inside field values:

- **`Relationships`** — `;`-separated `E-NN (<1:1|1:N|N:1|N:M>, <required|optional>) [note]`, or
  `none`. Cardinality reads *this : other*; `required` means this entity cannot exist without the
  link. The first required `N:1` link is the entity's parent in the generated relationship tree.
  When both sides declare each other the cardinalities must be inverse (`RELATIONSHIP_INCONSISTENT`).
- **`Deletion semantics`** — starts with `cascade`, `soft-delete`, `archive`, `restrict` or
  `orphan-allowed`; free text may follow (`archive — archived projects can be restored`).
- **`Mutable fields`** — `none …` marks an immutable entity; otherwise the entity (or one linked
  through `Features` whose name says create/edit/delete/assign/…) needs at least one `PR` rule.
- **`Grants`** — `,`-separated `RL-NN <cell>`, one per active role, cells `✓` `✗` `Limited` `?`.
  `Limited` needs `Limited means`; `?` needs a `Related unknown` U record. One active rule per
  resource × action (`DUPLICATE_PERMISSION_RULE`); a corrected rule gets a new title and supersedes
  the old one by amendment.
- **Competitors** — `C` `Table-stakes features` lists the target features the competitor offers;
  scripts count them (≥ 2 competitors = table stakes, 1 = rare). `FS` `Signal` is `table-stakes`
  (≥ 2 competitors), `rare` (exactly 1), `differentiator` or `absent-in-target` (its `Feature` is a
  capability name, not an F ID). Competitor sources carry `Relevant area: competitor:<C-ID>`.
- **Score cards** — each `SC` criterion is `<0-3> — <rationale>`; `Future` is `yes`/`maybe`/`no`;
  `Override decision` (one of the five decisions) needs `Override reason`. Scores and overrides are
  amendable (`### AMEND SC-NNN`); priorities and decisions are never written — `pf.py score`
  computes them. `R` `Priority` is `must`/`should`; `UD` names its `Unknown`.
- **Architecture** — `ADR` `Alternatives` are `;`-separated (≥ 2), `Topic` is a mandatory topic
  or `other`, `Status` is `accepted` | `global` | `superseded-by ADR-…`; `INV` `Enforced by` starts
  with `test`, `middleware`, `db-constraint`, `lint` or `review`; one `AP` per `A` (amendable:
  `Proposed implementation`, `Decision`); an ADR that contradicts a requirement names it in
  `Deviates from` (R IDs; `ADR_DEVIATES_FROM_REQUIREMENT` warns with the `reopen` hint).
- Optional `Human-readable key` and `Stable after creation` (`yes`/`no`/`unknown`) feed the
  generated identity table; `RL` `Scope` is `workspace`, `team`, `resource` or `system`.

## Validator finding codes

Reported by `pf.py validate` / `check` as findings (`error` findings make the command exit 1 and
fail the stage's `G-VALIDATE-CLEAN` gate condition; `warn` findings are advisory). Validation is
tolerant: a malformed record yields one finding and the rest of the file is still checked.

| Code | Severity | Meaning |
|---|---|---|
| `PARSE_ERROR` | error | Malformed record heading, field line, continuation or duplicate field |
| `DUPLICATE_ID` | error | The same record ID is defined more than once |
| `UNKNOWN_PREFIX` | error | A record's prefix is unknown or does not belong in this artifact |
| `MISSING_FIELD` | error | A required field is absent |
| `EMPTY_FIELD` | error | A required field is empty (and the schema does not allow it) |
| `UNKNOWN_FIELD` | warn | A field that is not part of the record's schema |
| `DANGLING_REF` | error | A reference to an ID that does not exist |
| `WRONG_REF_TYPE` | error | A reference field cites a record of the wrong type |
| `BAD_ENUM` | error | A field holds a value outside its closed set |
| `FIELD_NOT_YET_ALLOWED` | error | A field that does not belong on this record type yet |
| `PARENT_DOMAIN_MISMATCH` | error | A feature's parent is in a different domain |
| `PARENT_CYCLE` | error | Features form a parent cycle |
| `GENERATED_REGION_EDITED` | error | A generated region differs from a fresh render |
| `BAD_STEPS` | error | A workflow has no numbered steps, or they are not numbered 1..n |
| `BAD_STEP_TAG` | error | A workflow step lacks an [observed] or [implied-system] tag |
| `OBSERVED_STEP_NO_EVIDENCE` | error | An [observed] workflow step cites no S-/D- evidence |
| `NO_SYSTEM_STEPS` | warn | A workflow lists no [implied-system] steps |
| `WORKFLOW_CONFIDENCE` | error | A CONFIRMED workflow's observed steps lack Tier ≤ 2 evidence |
| `BAD_RELATIONSHIP` | error | A relationship does not follow 'E-NN (<card>, <required>)' |
| `RELATIONSHIP_INCONSISTENT` | warn | Two entities link each other with clashing cardinality |
| `BAD_DELETION_SEMANTICS` | error | Deletion semantics lacks a known deletion kind |
| `BAD_GRANT` | error | A permission cell is not '<RL-ID> <✓|✗|Limited|?>' |
| `PERMISSION_CELL_MISSING` | error | A permission rule has no cell for an active role |
| `UNKNOWN_CELL_NO_U` | error | A '?' permission cell without a Related unknown U record |
| `LIMITED_WITHOUT_MEANS` | error | A 'Limited' permission cell without 'Limited means' |
| `ENTITY_WITHOUT_PERMISSIONS` | error | A mutable entity has no permission rules |
| `DUPLICATE_PERMISSION_RULE` | error | Two active permission rules for one resource and action |
| `TARGET_IMPL_UNSUPPORTED` | error | Target implementation is stated without evidence |
| `REQUIREMENT_NOT_MEASURABLE` | warn | Our requirement has no measurable element |
| `TECH_ASSERTION_IN_OBSERVATION` | warn | An observation names a technology no evidence states |
| `BAD_FEATURE_SIGNAL` | error | A feature signal's Feature or Competitors do not fit its kind |
| `TABLE_STAKES_UNDERSUPPORTED` | error | A table-stakes signal names fewer than 2 competitors |
| `COMPLAINT_SOURCE_TIER` | error | Competitor complaints do not cite Tier 3–4 sources |
| `COMPETITOR_SOURCE_AS_EVIDENCE` | error | A target record cites a competitor's source |
| `COMPETITOR_OVER_BUDGET` | warn | A competitor has more sources than competitors.max_sources |
| `BAD_SCORE` | error | A score is not '<0-3> — <rationale>' |
| `OVERRIDE_NO_REASON` | error | An override decision has no Override reason |
| `SIMPLIFICATION_MISSING` | error | A BUILD SIMPLIFIED feature does not say what is left out |
| `EXTERNAL_SERVICE_MISSING` | error | A USE EXTERNAL SERVICE feature names no service |
| `FEATURE_UNSCORED` | error | A feature has no score card once scoring has started |
| `DUPLICATE_SCORE` | error | A feature has more than one active score card |
| `FEATURE_WITHOUT_REQUIREMENT` | error | A feature built in V1 is in no requirement |
| `ADR_NO_ALTERNATIVES` | error | An ADR lists fewer than two alternatives |
| `INVARIANT_UNENFORCED` | error | An invariant names no enforcement mechanism |
| `ARCHITECTURE_DISCLAIMER_MISSING` | error | ARCHITECTURE.md does not say it is ours |
| `STACK_INCOMPLETE` | error | The stack table is missing or has open choices |
| `BAD_REPO_TREE` | error | The repository structure is not a parseable tree |
| `UNJUSTIFIED_COMPONENT` | warn | A component cites no requirement, inference or ADR |
| `REQUIREMENT_UNADDRESSED` | error | A requirement is addressed by no ADR or convention |
| `INFERENCE_UNPROPOSED` | error | An inference has no proposal, or more than one |
| `ADR_TOPIC_MISSING` | error | A mandatory topic has no ADR and no not-applicable reason |
| `SUPERSEDED_DECISION_CITED` | warn | A proposal still cites a superseded ADR |
| `ADR_DEVIATES_FROM_REQUIREMENT` | warn | A decision deviates from a requirement |
| `ENTITY_LOOKS_LIKE_UI_STATE` | warn | An entity's name suggests UI state, not an entity |
| `PHASE_HEADER_FIELDS` | error | A phase lacks its title line or Status / Depends on / Goal |
| `PHASE_HEADING_MISSING` | error | A phase lacks one of the §16.2 headings |
| `PHASE_HEADING_ORDER` | error | A phase's §16.2 headings are out of order |
| `PHASE00_HAS_DEPS` | error | Phase 00 depends on another phase |
| `PHASE_DEP_UNKNOWN` | error | A phase depends on a phase that does not exist |
| `PHASE_DEP_FORWARD` | error | A phase depends on a later phase |
| `PHASE_DEP_CYCLE` | error | Phase dependencies form a cycle |
| `PHASE_SECTION_REF_DANGLING` | error | A phase cites a § that does not exist |
| `PHASE_TASK_NO_PATH` | error | A phase task names no path |
| `PHASE_PATH_OUTSIDE_TREE` | error | A phase task names a path outside the repository tree |
| `PHASE_TOO_FEW_ACCEPTANCE` | error | A phase has fewer than phases.min_acceptance criteria |
| `PHASE_TOO_MANY_TASKS` | error | A phase has more than phases.max_tasks tasks |
| `PHASE_INDEX_MISMATCH` | error | Plans index, phase files and the plan's breakdown disagree |
| `PHASE_ID_REF_DANGLING` | error | A phase's References cite a record that does not exist |
| `ROOTDOC_SECTION_MISSING` | error | A generated root document lacks a required section |
| `TRACE_R_NOT_PLANNED` | error | A requirement for V1 features is cited by no phase |
| `TRACE_ADR_UNUSED` | error | A decision is cited by no phase and is not Status: global |
| `TRACE_INV_UNUSED` | error | An invariant reaches neither CLAUDE.md, the index nor a phase |
| `TRACE_D_NO_SOURCE` | error | A claim reaches no source through its evidence |
| `TRACE_F_NO_EVIDENCE` | error | A feature reaches no claim or source |
| `TRACE_PHASE_NO_REQUIREMENT` | warn | A phase after 00 cites no R, ADR or INV |
| `TRACE_DROPPED_FEATURE_PLANNED` | error | A phase plans a requirement of deferred features |
| `BAD_STATUS` | error | Status is not one of the allowed values (or rejected without Reason) |
| `SUPERSEDED_TARGET_MISSING` | error | superseded-by targets a missing or other-type record |
| `PROVISIONAL_ID_IN_CANONICAL` | error | A provisional ID (X-?n) appears in a canonical file |
| `NEAR_DUPLICATE_TITLE` | warn | Two records of the same type have nearly identical titles |
| `QUOTE_TOO_LONG` | error | A verbatim quote is longer than quotes.max_words |
| `BAD_CONFIDENCE` | error | Confidence is not CONFIRMED, PROBABLE, INFERRED or UNKNOWN |
| `CONFIDENCE_RULE` | error | The cited evidence does not support the stated confidence (§11) |
| `PROVIDER_REPORT_AS_EVIDENCE` | error | A claim above INFERRED rests only on a skill's report |
| `CONFLICT_ASYMMETRIC` | error | A conflict is declared on one side only |
| `CONFLICT_UNRESOLVED` | warn | A conflicting pair has no unknown or Resolution explaining it |
| `BAD_TIER` | error | Source tier is not an integer 1–5 |
| `BAD_CATEGORY` | error | Source category is not in the taxonomy |
| `BAD_AUTHORITY` | error | Source authority is not High, Medium or Low |
| `TIER_RAISED` | error | Tier is better than the category default (only lowering) |
| `CANONICAL_URL_MISMATCH` | error | Canonical URL is not the canonical form of URL |
| `DUPLICATE_SOURCE` | error | Two sources share a canonical URL |
| `LOCK_VIOLATION` | error | A record of a closed stage was modified or lost references |
| `LOCK_DELETED` | error | A record of a closed stage was deleted |

Every record with a `Confidence` field also accepts optional `Derived from` and `Related unknown`
reference lists (needed by the INFERRED and UNKNOWN rules — see `confidence-rules.md`). `Reason` is
accepted on any record and required with `Status: rejected`.
