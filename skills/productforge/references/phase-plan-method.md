# Phase Plan Method

How PHASE_PLAN_READY turns the locked spec into a project a fresh Claude Code session can build
(IMPLEMENTATION_PLAN.md §16, IDEA §27–§31). `pf.py lint-phases` (`pflib/phaselint.py`) is the
authority on whether a plan is valid; this repository's own `plans/v1/` passes the same lint.

## Principles

1. **The architecture lives in repository files**, not in chat: `IMPLEMENTATION_PLAN.md` (21
   numbered sections), `CLAUDE.md` (golden rules = invariants), `DEVELOPMENT.md`, `README.md`,
   `STARTUP_PROMPT.md`, `plans/README.md` and `plans/phase-NN-<slug>.md`.
2. **Each phase is independently executable in one session**: it names what to read, what to
   build (exact paths), how to verify, and how to update the ledger.
3. **No new decisions while planning.** Every choice comes from the spec (R, ADR, INV, E, …). A gap
   is a research request to the systems-architect, never a decision made in a phase file.
4. **Traceability**: each phase's `## References` lists the IMPLEMENTATION_PLAN §N sections and the
   R / ADR / INV IDs it implements.

## The phase file (§16.2, verbatim)

```markdown
# Phase NN — <Name>

**Status:** Not started
**Depends on:** <phase numbers, or "none">
**Goal:** <one sentence>

## Context
## Scope
**In:** …
**Out / deferred:** …
## Tasks
## Data & schema changes
## API / contracts
## Acceptance criteria
## Test plan
## References
## Open questions / risks
## Definition of done
```

Lint rules: headings present and in order; the three header lines; phase 00 depends on none; a
phase depends only on existing, lower-numbered phases, with no cycle; every `§N`/`§N.M` exists in
`IMPLEMENTATION_PLAN.md`; every numbered task names a path in backticks inside the repository tree
(`spec/ARCHITECTURE.md` `## Repository structure`, plus `research/`, `spec/`, `plans/`); at least
`phases.min_acceptance` (3) `- [ ]` criteria; at most `phases.max_tasks` (15) tasks;
`plans/README.md`, the files and §19 list the same phases; References cite existing IDs.

## Sizing

One session per phase: at most `phases.max_tasks` tasks, usually 3–8. A phase too big for one
session is split; two trivial phases are merged.

## Ordering

foundation (repo, tooling, CI, test harness) → data and tenancy → identity and sign-in →
authorization → core domain entities in dependency order (the relationship tree, roots first) →
cross-cutting features (search, realtime, notifications, jobs) → integrations → audit and
observability → deployment hardening. A phase depends only on what it truly needs, so independent
phases can run in parallel.

## Root documents

- `IMPLEMENTATION_PLAN.md` — exactly the 21 numbered sections (1 Product overview … 21 Glossary);
  section 1 starts with the provenance line; §19 is the phase table `| # | Phase | Depends on |
  Delivers |`.
- `CLAUDE.md` — `## Golden rules`: one numbered rule per invariant, in INV order (rule — reason —
  enforced by); plus stack, layout, commands, conventions, security, extension recipes,
  anti-patterns, testing expectations and the "Executing a phase" protocol.
- `DEVELOPMENT.md`, `README.md`, `STARTUP_PROMPT.md` — the template headings, filled for the stack.
