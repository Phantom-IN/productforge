# Plan review — the consistency checklist

`pf.py lint-phases` checks each phase and a few rules across phases. It cannot read meaning. The
consistency review does: one phase-planner run reads every root document and every phase file and
looks for the mismatches that a hand-made plan needed three review rounds to remove. Run it after
Lint (`references/commands-finalize.md`, step "Consistency review").

## Reviewer's stance

Read the whole plan as the builder of each phase would, in table order, holding only that phase's
dependencies in mind. Whatever a phase uses must already exist, with the same spelling, in a
dependency or in the spec. Check against `spec/ARCHITECTURE.md`, `spec/decisions/` and
`DEVELOPMENT.md`, not against memory.

## Checklist

1. **Names.** Functions, modules, tables, columns and types are spelled the same everywhere. A phase
   that calls a helper uses the name the creating phase gave it.
2. **Routes and methods.** Each route has one path, one method and one owner phase. Clients and
   tests call what the API phase declares.
3. **Environment variables.** Every variable named in a phase is in `DEVELOPMENT.md`
   (## Environment variables) and in the architecture's ## Environments, with the same name.
4. **Error codes and statuses.** Each code has one meaning and one HTTP or exit status. A phase
   does not invent a code the contract phase never defined.
5. **Policy actions and permission rows.** Every action a phase enforces has a row in the
   permissions matrix, and every row is enforced by some phase.
6. **Registries defined before use.** Route, policy, job, event and feature-flag registries are
   created by an earlier phase than the one that adds an entry to them.
7. **Jobs.** Job names, payloads and dedupe keys match between the phase that enqueues and the one
   that handles.
8. **File paths.** A path is created by one phase; later phases that edit it depend on that phase
   (lint warns `PHASE_PATH_CREATOR_NOT_DEP`; the review also catches renamed paths).
9. **Migrations.** Numbering is gapless in table order; no phase edits a migration an earlier phase
   shipped; a table exists before any foreign key points at it.
10. **Services and ports.** Compose services, images, ports and volumes agree between
    `DEVELOPMENT.md`, the architecture and the phases that start them; no two services share a port.
11. **CI.** The CI file is created once, and its commands are the ones `DEVELOPMENT.md` lists.
12. **Leftovers from rejected options.** No phase, document or glossary entry still mentions an
    option an ADR rejected or a feature the parity matrix defers.
13. **Dependencies.** Each `**Depends on:**` list names every phase whose output the phase uses and
    no more; phases that could run in parallel do not depend on each other.
14. **Open questions.** No open question asks the builder to choose; each is a decision (named in an
    ADR) or a recorded risk.

## Reporting a finding

Write one `### REVISE <path>` block per finding in the run's report, then apply every fix by
staging the corrected file under the same path (phase files and root documents are documents:
merge replaces them section by section, so stage only the sections that change). Never leave a
finding as prose advice.

```text
### REVISE plans/phase-07-board-and-polling.md
Line: 31
Finding: calls `getBoardColumns` but phase 06 names it `listStatuses` (plans/phase-06-tasks-and-statuses.md:24)
Fix: rename the call to `listStatuses`
```

Give `file:line` of the offending text, the conflicting source with its own `file:line`, and the
exact fix. When two files disagree and the spec decides, fix the one that departs from the spec.
When the spec does not decide, add a `RESEARCH REQUESTS` entry instead of choosing.

## Stopping

A round with no finding ends the review. The run stops after `finalize.review_rounds` rounds even
if findings remain; report the remainder to the user instead of looping.
