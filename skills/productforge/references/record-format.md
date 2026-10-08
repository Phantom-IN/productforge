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
| `BAD_STATUS` | error | Status is not one of the allowed values (or rejected without Reason) |
| `SUPERSEDED_TARGET_MISSING` | error | superseded-by targets a missing or other-type record |
| `PROVISIONAL_ID_IN_CANONICAL` | error | A provisional ID (X-?n) appears in a canonical file |
| `NEAR_DUPLICATE_TITLE` | warn | Two records of the same type have nearly identical titles |
| `QUOTE_TOO_LONG` | error | A verbatim quote is longer than quotes.max_words |
| `BAD_CONFIDENCE` | error | Confidence is not CONFIRMED, PROBABLE, INFERRED or UNKNOWN |
| `CONFIDENCE_RULE` | error | The cited evidence does not support the stated confidence (§11) |
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
